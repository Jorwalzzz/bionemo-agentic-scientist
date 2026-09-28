"""Integration tests for the Agentic BioNeMo Orchestrator."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import os
import pytest
from src.orchestrator import AgenticScientistOrchestrator

def test_full_orchestration_cycle(tmp_path):
    orchestrator = AgenticScientistOrchestrator(mock=True)
    out_dir = str(tmp_path / "test_results")
    
    dossier = orchestrator.run_discovery_campaign(
        target_query="EGFR T790M",
        num_candidates=6,
        enable_feedback_loop=True,
        output_dir=out_dir
    )
    
    assert dossier.target.name == "EGFR T790M"
    assert len(dossier.top_leads) > 0
    assert dossier.screened_count >= 6
    assert len(dossier.agent_audit_log) >= 5
    
    # Check generated files
    assert os.path.exists(os.path.join(out_dir, "CANDIDATE_SELECTION_DOSSIER.md"))
    assert os.path.exists(os.path.join(out_dir, "screened_candidates_summary.csv"))
    assert os.path.exists(os.path.join(out_dir, "top_leads_docked.sdf"))
