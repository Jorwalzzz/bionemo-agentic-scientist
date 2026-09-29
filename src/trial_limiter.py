"""
Agentic BioNeMo - Enterprise Anti-Bypass Trial Rate Limiter & Fingerprinting Engine

Provides 6 comprehensive security layers to strictly protect private NVIDIA API credits & compute:
1. Strict 1-Run Limit per device / session / IP / subnet.
2. Global Daily Circuit Breaker (hard ceiling on maximum runs across all users globally/day).
3. Cloudflare & Reverse-Proxy True IP Extraction (CF-Connecting-IP & X-Forwarded-For).
4. Cryptographically signed HMAC-SHA256 HttpOnly session cookies.
5. High-entropy client canvas/WebGL/hardware fingerprint hashing (anti-incognito).
6. Anti-Bot Scraper Shield (blocks curl, python-requests, automated scrapers).
"""

import os
import sys
import json
import time
import hmac
import hashlib
import ipaddress
import secrets
import tempfile
import threading
from typing import Dict, Any, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

LEDGER_PATH = os.environ.get("TRIAL_LEDGER_PATH", os.path.join(DATA_DIR, "trial_ledger.json"))
SECRET_KEY_PATH = os.path.join(DATA_DIR, ".trial_secret")
MAX_TRIAL_RUNS = int(os.environ.get("MAX_TRIAL_RUNS", "2"))
MAX_SUBNET_RUNS = int(os.environ.get("MAX_SUBNET_RUNS", "4"))
MAX_GLOBAL_DAILY_RUNS = int(os.environ.get("MAX_GLOBAL_DAILY_RUNS", "25"))

# Disallowed automated bot scrapers attempting to call /api/run
BLOCKED_USER_AGENTS = (
    "curl", "python-requests", "aiohttp", "wget", "httpie",
    "postmanruntime", "scrapy", "go-http-client", "apache-httpclient"
)


def _get_or_create_secret_key() -> bytes:
    """Retrieve or initialize persistent HMAC secret key."""
    if os.environ.get("TRIAL_SECRET_KEY"):
        return os.environ["TRIAL_SECRET_KEY"].encode("utf-8")
    if os.path.exists(SECRET_KEY_PATH):
        try:
            with open(SECRET_KEY_PATH, "rb") as f:
                key = f.read().strip()
                if len(key) >= 32:
                    return key
        except Exception:
            pass
    key = secrets.token_bytes(32)
    try:
        with open(SECRET_KEY_PATH, "wb") as f:
            f.write(key)
    except Exception:
        pass
    return key


class TrialLimiter:
    """Thread-safe, anti-exploit trial rate limiter with persistent disk state & global circuit breaker."""

    def __init__(
        self,
        ledger_path: str = LEDGER_PATH,
        max_runs: int = MAX_TRIAL_RUNS,
        max_subnet_runs: int = MAX_SUBNET_RUNS,
        max_global_daily_runs: int = MAX_GLOBAL_DAILY_RUNS
    ):
        self.ledger_path = ledger_path
        self.max_runs = max_runs
        self.max_subnet_runs = max_subnet_runs
        self.max_global_daily_runs = max_global_daily_runs
        self._secret_key = _get_or_create_secret_key()
        self._lock = threading.Lock()
        self._ledger: Dict[str, Any] = self._load_ledger()

    def _load_ledger(self) -> Dict[str, Any]:
        """Load ledger from disk or initialize empty ledger."""
        default_ledger = {
            "version": 2,
            "max_runs": self.max_runs,
            "daily_usage": {},  # "YYYY-MM-DD" -> count
            "sessions": {},     # session_id -> {runs, created_at, last_used, ips, fps}
            "fingerprints": {}, # fp_hash -> {runs, first_seen, last_seen, ips, sessions}
            "ips": {},          # ip -> {runs, first_seen, last_seen, sessions}
            "subnets": {},      # subnet -> count
            "history": []       # [{timestamp, session_id, ip, fp, target, runs_after}]
        }
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "sessions" in data:
                        if "daily_usage" not in data:
                            data["daily_usage"] = {}
                        return data
            except Exception as e:
                print(f"[TrialLimiter] Warning: could not load ledger, reinitializing: {e}")
        return default_ledger

    def _save_ledger(self) -> None:
        """Atomically persist ledger to disk using temp file replacement."""
        dir_name = os.path.dirname(self.ledger_path)
        os.makedirs(dir_name, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
                json.dump(self._ledger, tf, indent=2)
                temp_name = tf.name
            os.replace(temp_name, self.ledger_path)
        except Exception as e:
            print(f"[TrialLimiter] Error writing ledger to disk: {e}")

    # ─────────────────────────────────────────────────────────────
    # Bot Shield & Token Handling
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def is_bot_user_agent(user_agent: Optional[str]) -> bool:
        """Check if incoming request is from an automated scraping tool."""
        if not user_agent:
            return False
        ua_lower = user_agent.lower().strip()
        return any(bot in ua_lower for bot in BLOCKED_USER_AGENTS)

    def create_signed_session_token(self, session_id: Optional[str] = None) -> str:
        """Generate a tamper-proof session token: <session_id>:<timestamp>:<hmac_signature>"""
        if not session_id:
            session_id = secrets.token_hex(16)
        ts = str(int(time.time()))
        payload = f"{session_id}:{ts}"
        sig = hmac.new(self._secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload}:{sig}"

    def verify_and_extract_session(self, token_str: Optional[str]) -> Optional[str]:
        """Validate HMAC signature of incoming session token and extract session_id."""
        if not token_str or not isinstance(token_str, str):
            return None
        parts = token_str.strip().split(":")
        if len(parts) != 3:
            return None
        session_id, ts, sig = parts
        payload = f"{session_id}:{ts}"
        expected_sig = hmac.new(self._secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return session_id
        return None

    # ─────────────────────────────────────────────────────────────
    # IP & Subnet Normalization
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def normalize_ip(ip_str: str) -> Tuple[str, str]:
        """
        Normalize IPv4/IPv6 address and extract /24 (IPv4) or /48 (IPv6) subnet.
        Handles localhost loopbacks gracefully.
        """
        ip_str = ip_str.strip()
        if ip_str in ("127.0.0.1", "::1", "localhost", "testclient"):
            return "127.0.0.1", "127.0.0.1/32"
        try:
            obj = ipaddress.ip_address(ip_str)
            if obj.version == 4:
                net = ipaddress.ip_network(f"{ip_str}/24", strict=False)
                return str(obj), str(net)
            else:
                net = ipaddress.ip_network(f"{ip_str}/48", strict=False)
                return str(obj), str(net)
        except ValueError:
            return ip_str, ip_str

    @staticmethod
    def compute_composite_fingerprint(
        client_fp: Optional[str],
        user_agent: Optional[str],
        accept_lang: Optional[str] = None
    ) -> str:
        """Compute high-entropy SHA-256 fingerprint from client hardware canvas/webgl hash."""
        raw = f"{client_fp or 'unknown_fp'}|{user_agent or 'unknown_ua'}|{accept_lang or 'unknown_lang'}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    # ─────────────────────────────────────────────────────────────
    # Trial Limit Evaluation & Consumption
    # ─────────────────────────────────────────────────────────────

    def check_usage(
        self,
        session_id: Optional[str],
        fp_hash: str,
        ip_str: str
    ) -> Dict[str, Any]:
        """Check current trial usage without consuming."""
        with self._lock:
            today = time.strftime("%Y-%m-%d", time.gmtime())
            daily_count = self._ledger.get("daily_usage", {}).get(today, 0)
            if daily_count >= self.max_global_daily_runs:
                return {
                    "allowed": False,
                    "runs_used": self.max_runs,
                    "runs_remaining": 0,
                    "max_runs": self.max_runs,
                    "is_locked": True,
                    "circuit_breaker_active": True,
                    "reason": "Global daily demo quota reached. Please use the Local 1-Click Installer."
                }

            norm_ip, subnet = self.normalize_ip(ip_str)

            session_runs = 0
            if session_id and session_id in self._ledger["sessions"]:
                session_runs = self._ledger["sessions"][session_id].get("runs", 0)

            fp_runs = 0
            if fp_hash and fp_hash in self._ledger["fingerprints"]:
                fp_runs = self._ledger["fingerprints"][fp_hash].get("runs", 0)

            is_local = norm_ip == "127.0.0.1"
            ip_runs = 0
            if not is_local and norm_ip in self._ledger["ips"]:
                ip_runs = self._ledger["ips"][norm_ip].get("runs", 0)

            subnet_runs = 0
            if not is_local and subnet in self._ledger["subnets"]:
                subnet_runs = self._ledger["subnets"].get(subnet, 0)

            runs_used = max(session_runs, fp_runs, ip_runs)
            runs_remaining = max(0, self.max_runs - runs_used)
            allowed = runs_used < self.max_runs

            if not is_local and subnet_runs >= self.max_subnet_runs:
                allowed = False
                reason = f"Subnet trial quota exceeded ({subnet_runs}/{self.max_subnet_runs})"
            elif not allowed:
                reason = f"Free trial limit reached ({runs_used}/{self.max_runs} runs used)"
            else:
                reason = "Trial run available"

            return {
                "allowed": allowed,
                "runs_used": runs_used,
                "runs_remaining": runs_remaining,
                "max_runs": self.max_runs,
                "session_runs": session_runs,
                "fp_runs": fp_runs,
                "ip_runs": ip_runs,
                "is_locked": not allowed,
                "circuit_breaker_active": False,
                "reason": reason
            }

    def consume_trial_run(
        self,
        session_id: str,
        fp_hash: str,
        ip_str: str,
        target_name: str = "Unknown",
        user_agent: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Atomically verify availability and consume 1 trial run."""
        # 1. Anti-Bot Filter
        if self.is_bot_user_agent(user_agent):
            return False, {
                "allowed": False,
                "error": "BOT_REQUEST_FORBIDDEN",
                "message": "Automated scripts are blocked on the trial demo to protect API credits. Launch the Local App for script access."
            }

        with self._lock:
            # 2. Global Circuit Breaker (Hard Ceiling per calendar day)
            today = time.strftime("%Y-%m-%d", time.gmtime())
            if "daily_usage" not in self._ledger:
                self._ledger["daily_usage"] = {}
            daily_count = self._ledger["daily_usage"].get(today, 0)

            if daily_count >= self.max_global_daily_runs:
                return False, {
                    "allowed": False,
                    "runs_used": self.max_runs,
                    "runs_remaining": 0,
                    "max_runs": self.max_runs,
                    "is_locked": True,
                    "error": "GLOBAL_DAILY_LIMIT_REACHED",
                    "message": "Today's global discovery quota has been reached to protect server & API credits. Launch the Local App for unlimited execution."
                }

            norm_ip, subnet = self.normalize_ip(ip_str)
            is_local = norm_ip == "127.0.0.1"

            # 3. Individual user / device limit
            session_runs = self._ledger["sessions"].get(session_id, {}).get("runs", 0)
            fp_runs = self._ledger["fingerprints"].get(fp_hash, {}).get("runs", 0)
            ip_runs = self._ledger["ips"].get(norm_ip, {}).get("runs", 0) if not is_local else 0
            subnet_runs = self._ledger["subnets"].get(subnet, 0) if not is_local else 0

            current_runs = max(session_runs, fp_runs, ip_runs)

            if current_runs >= self.max_runs:
                return False, {
                    "allowed": False,
                    "runs_used": current_runs,
                    "runs_remaining": 0,
                    "max_runs": self.max_runs,
                    "is_locked": True,
                    "error": "TRIAL_LIMIT_EXCEEDED",
                    "message": f"Free trial limit reached ({current_runs}/{self.max_runs} run used). Launch the Full Local App for unlimited campaigns."
                }

            if not is_local and subnet_runs >= self.max_subnet_runs:
                return False, {
                    "allowed": False,
                    "runs_used": current_runs,
                    "runs_remaining": 0,
                    "max_runs": self.max_runs,
                    "is_locked": True,
                    "error": "SUBNET_QUOTA_EXCEEDED",
                    "message": "Subnet trial quota exceeded. Launch the Full Local App for unlimited access."
                }

            # 4. Increment all counters atomically
            new_run_count = current_runs + 1
            now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            # Update daily circuit breaker
            self._ledger["daily_usage"][today] = daily_count + 1

            # Update session
            if session_id not in self._ledger["sessions"]:
                self._ledger["sessions"][session_id] = {
                    "runs": 0, "created_at": now_ts, "ips": [], "fps": []
                }
            self._ledger["sessions"][session_id]["runs"] = new_run_count
            self._ledger["sessions"][session_id]["last_used"] = now_ts
            if norm_ip not in self._ledger["sessions"][session_id]["ips"]:
                self._ledger["sessions"][session_id]["ips"].append(norm_ip)
            if fp_hash not in self._ledger["sessions"][session_id]["fps"]:
                self._ledger["sessions"][session_id]["fps"].append(fp_hash)

            # Update fingerprint
            if fp_hash not in self._ledger["fingerprints"]:
                self._ledger["fingerprints"][fp_hash] = {
                    "runs": 0, "first_seen": now_ts, "ips": [], "sessions": []
                }
            self._ledger["fingerprints"][fp_hash]["runs"] = new_run_count
            self._ledger["fingerprints"][fp_hash]["last_seen"] = now_ts
            if norm_ip not in self._ledger["fingerprints"][fp_hash]["ips"]:
                self._ledger["fingerprints"][fp_hash]["ips"].append(norm_ip)
            if session_id not in self._ledger["fingerprints"][fp_hash]["sessions"]:
                self._ledger["fingerprints"][fp_hash]["sessions"].append(session_id)

            # Update IP & Subnet
            if not is_local:
                if norm_ip not in self._ledger["ips"]:
                    self._ledger["ips"][norm_ip] = {
                        "runs": 0, "first_seen": now_ts, "sessions": []
                    }
                self._ledger["ips"][norm_ip]["runs"] = new_run_count
                self._ledger["ips"][norm_ip]["last_seen"] = now_ts
                if session_id not in self._ledger["ips"][norm_ip]["sessions"]:
                    self._ledger["ips"][norm_ip]["sessions"].append(session_id)

                self._ledger["subnets"][subnet] = self._ledger["subnets"].get(subnet, 0) + 1

            # Audit record
            self._ledger["history"].append({
                "timestamp": now_ts,
                "session_id": session_id,
                "ip": norm_ip,
                "fp": fp_hash,
                "target": target_name,
                "run_number": new_run_count
            })

            # Save state to disk immediately
            self._save_ledger()

            runs_rem = max(0, self.max_runs - new_run_count)
            is_locked = (runs_rem == 0)
            return True, {
                "allowed": True,
                "runs_used": new_run_count,
                "runs_remaining": runs_rem,
                "max_runs": self.max_runs,
                "is_locked": is_locked,
                "message": f"Demo trial run {new_run_count} of {self.max_runs} completed. {runs_rem} free trial run(s) remaining."
            }

    def reset_caller(self, session_id: str, fp_hash: str, ip_str: str) -> None:
        """Resets usage for a specific caller so creator can test repeatedly."""
        with self._lock:
            norm_ip, subnet = self.normalize_ip(ip_str)
            self._ledger.get('ips', {}).pop(norm_ip, None)
            self._ledger.get("sessions", {}).pop(session_id, None)
            self._ledger.get("fingerprints", {}).pop(fp_hash, None)
            self._ledger.get("ips", {}).pop(ip_str, None)
            self._ledger.get("subnets", {}).pop(subnet, None)
            self._save_ledger()

    def reset_for_tests(self) -> None:
        """Utility for test suites to clear ledger state."""
        with self._lock:
            self._ledger = {
                "version": 2,
                "max_runs": self.max_runs,
                "daily_usage": {},
                "sessions": {},
                "fingerprints": {},
                "ips": {},
                "subnets": {},
                "history": []
            }
            if os.path.exists(self.ledger_path):
                try:
                    os.remove(self.ledger_path)
                except Exception:
                    pass
