"""
Unit & Security Tests for Anti-Bypass Trial Rate Limiter (2-Run Model).
Verifies that:
- Free trials allow exactly 2 runs (Target A vs Target B comparison), then strictly lock.
- Cryptographic HMAC session tokens detect tampering.
- Cookie clearing / Incognito window cannot bypass the 2-run limit (fingerprint & IP link).
- Fingerprint spoofing / curl cannot bypass the 2-run limit.
- State persists across server restarts.
- Anti-bot shield rejects curl/scrapers.
- Global daily circuit breaker halts execution when daily cap is reached.
"""

import os
import tempfile
import pytest
from src.trial_limiter import TrialLimiter


@pytest.fixture
def limiter():
    temp_dir = tempfile.mkdtemp()
    ledger_file = os.path.join(temp_dir, "test_trial_ledger_2runs.json")
    t = TrialLimiter(ledger_path=ledger_file, max_runs=2, max_subnet_runs=4, max_global_daily_runs=25)
    yield t
    if os.path.exists(ledger_file):
        try:
            os.remove(ledger_file)
        except Exception:
            pass


def test_hmac_session_token_integrity(limiter):
    token = limiter.create_signed_session_token("session_123")
    assert token is not None
    extracted = limiter.verify_and_extract_session(token)
    assert extracted == "session_123"

    # Tampered token should be rejected
    tampered = token[:-4] + "abcd"
    assert limiter.verify_and_extract_session(tampered) is None

    # Garbage token rejected
    assert limiter.verify_and_extract_session("invalid:token") is None
    assert limiter.verify_and_extract_session("") is None


def test_strict_two_runs_limit(limiter):
    session = "sess_user1"
    fp = "fp_hardware_hash_abc"
    ip = "198.51.100.25"

    # Initial check: 2 runs remaining
    status0 = limiter.check_usage(session, fp, ip)
    assert status0["allowed"] is True
    assert status0["runs_used"] == 0
    assert status0["runs_remaining"] == 2
    assert status0["is_locked"] is False

    # Run 1: Should succeed
    ok1, res1 = limiter.consume_trial_run(session, fp, ip, target_name="KRAS G12D")
    assert ok1 is True
    assert res1["runs_used"] == 1
    assert res1["runs_remaining"] == 1
    assert res1["is_locked"] is False

    # Check status: 1 run remaining
    status1 = limiter.check_usage(session, fp, ip)
    assert status1["allowed"] is True
    assert status1["runs_used"] == 1
    assert status1["runs_remaining"] == 1
    assert status1["is_locked"] is False

    # Run 2: Should succeed
    ok2, res2 = limiter.consume_trial_run(session, fp, ip, target_name="SARS-CoV-2 Mpro")
    assert ok2 is True
    assert res2["runs_used"] == 2
    assert res2["runs_remaining"] == 0
    assert res2["is_locked"] is True

    # Check status: locked
    status2 = limiter.check_usage(session, fp, ip)
    assert status2["allowed"] is False
    assert status2["runs_used"] == 2
    assert status2["runs_remaining"] == 0
    assert status2["is_locked"] is True

    # Run 3: MUST BE STRICTLY BLOCKED!
    ok3, res3 = limiter.consume_trial_run(session, fp, ip, target_name="EGFR T790M")
    assert ok3 is False
    assert res3["error"] == "TRIAL_LIMIT_EXCEEDED"
    assert res3["runs_remaining"] == 0
    assert res3["is_locked"] is True


def test_exploit_attempt_clearing_cookies(limiter):
    """User deletes cookies (new session_id), but same hardware fingerprint & IP."""
    fp = "fp_canvas_webgl_device_1"
    ip = "203.0.113.50"

    # User performs 2 allowed runs with Session A
    limiter.consume_trial_run("sess_A", fp, ip, "KRAS")
    limiter.consume_trial_run("sess_A", fp, ip, "Mpro")

    # Attacker clears cookies -> browser generates new session_B
    # But same device fingerprint & IP
    status = limiter.check_usage("sess_B", fp, ip)
    assert status["allowed"] is False
    assert status["runs_used"] == 2
    assert status["is_locked"] is True

    ok, res = limiter.consume_trial_run("sess_B", fp, ip, "EGFR")
    assert ok is False
    assert res["error"] == "TRIAL_LIMIT_EXCEEDED"


def test_exploit_attempt_incognito_different_browser(limiter):
    """User opens incognito in another browser: new session, different UA/fp, but SAME IP."""
    ip = "203.0.113.88"

    limiter.consume_trial_run("chrome_sess", "chrome_fp", ip, "KRAS")
    limiter.consume_trial_run("chrome_sess", "chrome_fp", ip, "Mpro")

    # Opens Firefox Incognito on same network/device -> blocked by IP & subnet
    status = limiter.check_usage("firefox_incognito_sess", "firefox_fp", ip)
    assert status["allowed"] is False
    assert status["runs_used"] == 2
    assert status["is_locked"] is True

    ok, res = limiter.consume_trial_run("firefox_incognito_sess", "firefox_fp", ip, "HER2")
    assert ok is False
    assert res["error"] == "TRIAL_LIMIT_EXCEEDED"


def test_persistence_across_server_restarts(limiter):
    """Ledger saved to disk must preserve counts when a new server instance boots."""
    session = "sess_persist"
    fp = "fp_persist"
    ip = "192.0.2.42"

    limiter.consume_trial_run(session, fp, ip, "KRAS")
    limiter.consume_trial_run(session, fp, ip, "Mpro")

    # Simulate server reboot by creating a fresh limiter pointing to the same file
    new_server_limiter = TrialLimiter(ledger_path=limiter.ledger_path, max_runs=2)
    status = new_server_limiter.check_usage(session, fp, ip)
    assert status["runs_used"] == 2
    assert status["runs_remaining"] == 0
    assert status["is_locked"] is True

    # 3rd run blocked on rebooted server
    ok3, res3 = new_server_limiter.consume_trial_run(session, fp, ip, "HER2")
    assert ok3 is False
    assert res3["error"] == "TRIAL_LIMIT_EXCEEDED"


def test_bot_user_agent_shield(limiter):
    """Automated curl / python-requests bots are immediately rejected."""
    ok, res = limiter.consume_trial_run(
        session_id="bot_sess",
        fp_hash="bot_fp",
        ip_str="198.51.100.99",
        user_agent="curl/8.1.2"
    )
    assert ok is False
    assert res["error"] == "BOT_REQUEST_FORBIDDEN"


def test_global_daily_circuit_breaker(limiter):
    """When global daily cap is reached, all further requests are blocked."""
    limiter.max_global_daily_runs = 2

    # User 1 run 1
    ok1, _ = limiter.consume_trial_run("u1", "fp1", "198.51.100.1")
    assert ok1 is True

    # User 2 run 1
    ok2, _ = limiter.consume_trial_run("u2", "fp2", "198.51.100.2")
    assert ok2 is True

    # User 3 attempts run -> Global Daily Cap reached!
    ok3, res3 = limiter.consume_trial_run("u3", "fp3", "198.51.100.3")
    assert ok3 is False
    assert res3["error"] == "GLOBAL_DAILY_LIMIT_REACHED"
