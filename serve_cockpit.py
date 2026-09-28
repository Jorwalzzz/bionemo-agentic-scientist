"""
Agentic BioNeMo - Production Web Cockpit Server (FastAPI)
Serves the Premium Bio-Computational Cockpit with:
- Multi-layer Anti-Bypass Trial Limiter (1 run limit + Global Daily Circuit Breaker + Bot Shield).
- Cloudflare & Reverse-Proxy True IP extraction.
- Automated installer download endpoints.
- Dynamic PORT support for Cloud / Hugging Face Spaces / Docker / Local.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.orchestrator import AgenticScientistOrchestrator
from src.trial_limiter import TrialLimiter

app = FastAPI(title="Agentic BioNeMo Cockpit API", version="2.2.0")

RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")

HTML_PATH = os.path.join(BASE_DIR, "stitch_cockpit.html")

COOKIE_NAME = "bionemo_trial_session"
trial_limiter = TrialLimiter()


def get_client_identifiers(request: Request) -> tuple:
    """Extract or issue tamper-proof session token, proxy-aware client IP, and composite fingerprint."""
    cookie_token = request.cookies.get(COOKIE_NAME)
    session_id = trial_limiter.verify_and_extract_session(cookie_token)
    if not session_id:
        signed_token = trial_limiter.create_signed_session_token()
        session_id = trial_limiter.verify_and_extract_session(signed_token)
    else:
        signed_token = cookie_token

    # Cloudflare / Reverse Proxy true client IP extraction
    cf_ip = request.headers.get("CF-Connecting-IP")
    xff = request.headers.get("X-Forwarded-For")
    x_real = request.headers.get("X-Real-IP")

    if cf_ip:
        client_ip = cf_ip.strip()
    elif xff:
        client_ip = xff.split(",")[0].strip()
    elif x_real:
        client_ip = x_real.strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    client_fp = request.headers.get("X-Client-Fingerprint") or request.query_params.get("fp")
    user_agent = request.headers.get("User-Agent")
    accept_lang = request.headers.get("Accept-Language")
    fp_hash = trial_limiter.compute_composite_fingerprint(client_fp, user_agent, accept_lang)

    return session_id, signed_token, fp_hash, client_ip, user_agent


@app.get("/", response_class=HTMLResponse)
def get_cockpit(request: Request):
    session_id, signed_token, _, _, _ = get_client_identifiers(request)
    if os.path.exists(HTML_PATH):
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        resp = HTMLResponse(content=content)
        resp.set_cookie(
            key=COOKIE_NAME,
            value=signed_token,
            max_age=86400 * 365,
            httponly=True,
            samesite="lax"
        )
        return resp
    return "<h1>Cockpit template not found.</h1>"


@app.get("/api/health")
@app.get("/healthz")
def get_health():
    return {
        "status": "healthy",
        "service": "Agentic BioNeMo Cockpit API",
        "version": "2.2.0",
        "trial_limit": trial_limiter.max_runs,
        "global_daily_cap": trial_limiter.max_global_daily_runs
    }


@app.get("/api/trial-status")
def get_trial_status(request: Request):
    """Check remaining trial runs for caller across session, fingerprint, IP, and global daily ceiling."""
    session_id, signed_token, fp_hash, client_ip, _ = get_client_identifiers(request)
    usage = trial_limiter.check_usage(session_id, fp_hash, client_ip)
    resp = JSONResponse(usage)
    resp.set_cookie(
        key=COOKIE_NAME,
        value=signed_token,
        max_age=86400 * 365,
        httponly=True,
        samesite="lax"
    )
    return resp


@app.get("/api/dossier")
def get_dossier():
    dossier_path = os.path.join(RESULTS_DIR, "CANDIDATE_SELECTION_DOSSIER.md")
    if os.path.exists(dossier_path):
        with open(dossier_path, "r", encoding="utf-8") as f:
            content = f.read()
        return Response(
            content=content, media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=CANDIDATE_SELECTION_DOSSIER.md"}
        )
    return JSONResponse({"status": "pending", "content": "No active dossier yet. Trigger a run first."})


@app.get("/api/download/installer-windows")
def download_windows_installer():
    path = os.path.join(BASE_DIR, "install.bat")
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "installer not found"})
    return FileResponse(
        path, filename="install.bat",
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=install.bat"}
    )


@app.get("/api/download/installer-unix")
def download_unix_installer():
    path = os.path.join(BASE_DIR, "install.sh")
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "installer not found"})
    return FileResponse(
        path, filename="install.sh",
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=install.sh"}
    )


@app.get("/api/setup-guide")
def get_setup_guide():
    return {
        "windows_powershell": "irm https://raw.githubusercontent.com/Jorwalzzz/bionemo-agentic-scientist/main/install.ps1 | iex",
        "unix_curl": "curl -sSL https://raw.githubusercontent.com/Jorwalzzz/bionemo-agentic-scientist/main/install.sh | bash",
        "docker": "git clone https://github.com/Jorwalzzz/bionemo-agentic-scientist.git && cd bionemo-agentic-scientist && docker compose up",
        "github": "https://github.com/Jorwalzzz/bionemo-agentic-scientist",
        "note": "Free Mock Mode works with zero API credits. Add NVIDIA_API_KEY to .env on your local instance for live GPU inference."
    }


@app.post("/api/run")
def trigger_run(request: Request, target: str = Query("KRAS G12D"), candidates: int = Query(10)):
    session_id, signed_token, fp_hash, client_ip, user_agent = get_client_identifiers(request)

    # 1. Clamp candidates to prevent single-request resource exhaustion
    safe_candidates = min(max(candidates, 1), 10)

    # 2. Strictly enforce trial limit & circuit breaker
    allowed, trial_info = trial_limiter.consume_trial_run(
        session_id=session_id,
        fp_hash=fp_hash,
        ip_str=client_ip,
        target_name=target,
        user_agent=user_agent
    )

    if not allowed:
        status_code = 429 if trial_info.get("error") == "GLOBAL_DAILY_LIMIT_REACHED" else 403
        resp = JSONResponse(status_code=status_code, content=trial_info)
        resp.set_cookie(key=COOKIE_NAME, value=signed_token, max_age=86400 * 365, httponly=True, samesite="lax")
        return resp

    # 3. Run Autonomous Discovery Campaign
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    use_mock = os.getenv("USE_MOCK", "false").lower() == "true" or not api_key
    orchestrator = AgenticScientistOrchestrator(api_key=api_key, mock=use_mock)
    dossier = orchestrator.run_discovery_campaign(
        target_query=target, num_candidates=safe_candidates, output_dir=RESULTS_DIR
    )

    result = {
        "status": "completed",
        "trial_status": trial_info,
        "target": dossier.target.name,
        "nominated_lead": dossier.top_leads[0].id if dossier.top_leads else "None",
        "binding_affinity": dossier.top_leads[0].binding_affinity if dossier.top_leads else 0.0,
        "screened": dossier.screened_count,
        "pareto_count": dossier.pareto_leads_count,
        "leads": [
            {
                "id": lead.id,
                "smiles": lead.smiles,
                "binding_affinity": lead.binding_affinity,
                "qed": lead.qed,
                "mw": lead.mw,
                "logp": lead.logp,
                "sascore": lead.sascore,
                "admet_verdict": lead.admet_verdict,
                "is_pareto": lead.is_pareto_optimal,
                "round": lead.generation_round,
            }
            for lead in dossier.top_leads
        ]
    }
    resp = JSONResponse(result)
    resp.set_cookie(key=COOKIE_NAME, value=signed_token, max_age=86400 * 365, httponly=True, samesite="lax")
    return resp


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
