"""
Agentic BioNeMo - High-Performance Web Cockpit Server (FastAPI)
Serves the Premium Bio-Computational Cockpit on http://localhost:8000.
Includes automated installer download endpoints for 1-click local setup.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.orchestrator import AgenticScientistOrchestrator

app = FastAPI(title="Agentic BioNeMo Cockpit API", version="2.0.0")

RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")

HTML_PATH = os.path.join(BASE_DIR, "stitch_cockpit.html")


@app.get("/", response_class=HTMLResponse)
def get_cockpit():
    if os.path.exists(HTML_PATH):
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Cockpit template not found.</h1>"


@app.get("/api/health")
def get_health():
    return {"status": "healthy", "service": "Agentic BioNeMo Cockpit API", "version": "2.0.0", "port": 8000}


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
def trigger_run(target: str = Query("KRAS G12D"), candidates: int = Query(10)):
    orchestrator = AgenticScientistOrchestrator(mock=True)
    dossier = orchestrator.run_discovery_campaign(
        target_query=target, num_candidates=candidates, output_dir=RESULTS_DIR
    )
    return {
        "status": "completed",
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
