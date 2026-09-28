"""
Agentic BioNeMo - High-Performance Web Cockpit Server (FastAPI)
Serves the Stitch-Engineered Bio-Computational Cockpit directly on http://localhost:8000.
"""
import os
import sys
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.orchestrator import AgenticScientistOrchestrator

app = FastAPI(title="Agentic BioNeMo Cockpit API")

# Ensure results dir is accessible
os.makedirs("results", exist_ok=True)
app.mount("/results", StaticFiles(directory="results"), name="results")

@app.get("/", response_class=HTMLResponse)
def get_cockpit():
    with open("stitch_cockpit.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/dossier")
def get_dossier():
    dossier_path = "results/CANDIDATE_SELECTION_DOSSIER.md"
    if os.path.exists(dossier_path):
        with open(dossier_path, "r", encoding="utf-8") as f:
            return {"status": "success", "content": f.read()}
    return {"status": "pending", "content": "No active dossier yet. Trigger a run first."}

@app.post("/api/run")
def trigger_run(target: str = "KRAS G12D", candidates: int = 10):
    orchestrator = AgenticScientistOrchestrator(mock=True)
    dossier = orchestrator.run_discovery_campaign(target_query=target, num_candidates=candidates, output_dir="results")
    return {
        "status": "completed",
        "target": dossier.target.name,
        "nominated_lead": dossier.top_leads[0].id if dossier.top_leads else "None",
        "binding_affinity": dossier.top_leads[0].binding_affinity if dossier.top_leads else 0.0,
        "screened": dossier.screened_count,
        "pareto_count": dossier.pareto_leads_count
    }

if __name__ == "__main__":
    uvicorn.run("serve_cockpit:app", host="0.0.0.0", port=8000, reload=True)
