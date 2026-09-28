"""
Agentic BioNeMo - High-Performance Web Cockpit Server (FastAPI)
Serves the Premium Bio-Computational Cockpit on http://localhost:8000.
Features:
- Anti-bypass 2-run free trial limit enforcement (HMAC tokens + Device Fingerprints + IP/Subnet Tracking).
- 1-Click automated local installer download endpoints.
- Real-time candidate dossier export.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.orchestrator import AgenticScientistOrchestrator
from src.trial_limiter import TrialLimiter

app = FastAPI(title="Agentic BioNeMo Cockpit API", version="2.1.0")

RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")

HTML_PATH = os.path.join(BASE_DIR, "stitch_cockpit.html")

COOKIE_NAME = "bionemo_trial_session"
trial_limiter = TrialLimiter()


def get_client_identifiers(request: Request) -> tuple:
    """Extract or issue tamper-proof session token, client IP, and composite fingerprint."""
    cookie_token = request.cookies.get(COOKIE_NAME)
    session_id = trial_limiter.verify_and_extract_session(cookie_token)
    if not session_id:
        signed_token = trial_limiter.create_signed_session_token()
        session_id = trial_limiter.verify_and_extract_session(signed_token)
    else:
        signed_token = cookie_token

    client_ip = request.client.host if request.client else "127.0.0.1"
    client_fp = request.headers.get("X-Client-Fingerprint") or request.query_params.get("fp")
    user_agent = request.headers.get("User-Agent")
    accept_lang = request.headers.get("Accept-Language")
    fp_hash = trial_limiter.compute_composite_fingerprint(client_fp, user_agent, accept_lang)

    return session_id, signed_token, fp_hash, client_ip


@app.get("/", response_class=HTMLResponse)
def get_cockpit(request: Request):
    session_id, signed_token, _, _ = get_client_identifiers(request)
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
def get_health():
    return {
        "status": "healthy",
        "service": "Agentic BioNeMo Cockpit API",
        "version": "2.1.0",
        "port": 8000,
        "trial_limit": trial_limiter.max_runs
    }


@app.get("/api/trial-status")
def get_trial_status(request: Request):
    """Check remaining free trial runs for the caller across session, fingerprint, and IP."""
    session_id, signed_token, fp_hash, client_ip = get_client_identifiers(request)
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
        "note": "Free Mock Mode works with no API key. Add NVIDIA_API_KEY to .env for live GPU inference."
    }


@app.post("/api/run")
def trigger_run(request: Request, target: str = Query("KRAS G12D"), candidates: int = Query(10)):
    session_id, signed_token, fp_hash, client_ip = get_client_identifiers(request)

    # Strictly enforce trial limit (max 2 runs)
    allowed, trial_info = trial_limiter.consume_trial_run(
        session_id=session_id,
        fp_hash=fp_hash,
        ip_str=client_ip,
        target_name=target
    )

    if not allowed:
        resp = JSONResponse(status_code=403, content=trial_info)
        resp.set_cookie(key=COOKIE_NAME, value=signed_token, max_age=86400 * 365, httponly=True, samesite="lax")
        return resp

    # Run Autonomous Discovery
    orchestrator = AgenticScientistOrchestrator(mock=True)
    dossier = orchestrator.run_discovery_campaign(
        target_query=target, num_candidates=candidates, output_dir=RESULTS_DIR
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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
