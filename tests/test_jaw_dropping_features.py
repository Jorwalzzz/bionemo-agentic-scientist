"""
Unit and integration tests for the three jaw-dropping NVIDIA BioNeMo features:
1. Adaptive Resistance Escape Engine (ESM-2 + MolMIM).
2. Automated FDA IND Clinical Dossier Generator (PDF).
3. Opentrons OT-2 Robotic Liquid Handler Protocol Generator.
"""

import ast
import pytest
from fastapi.testclient import TestClient

from serve_cockpit import app
from src.ind_dossier import generate_ind_pdf
from src.models import MoleculeCandidate, RetrosynthesisPlan, RetrosynthesisStep, TargetProfile
from src.resistance_engine import ResistanceEscapeEngine
from src.robot_protocol import generate_lab_card, generate_ot2_protocol


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# Feature 2: FDA IND Dossier PDF Tests
# ==============================================================================
def test_ind_dossier_pdf_generation():
    """Verify FDA IND Section 2 PDF generates valid PDF binary data."""
    sample_dossier = {
        "target": "KRAS G12D",
        "pdb_id": "8AZV",
        "nominated_lead": "LEAD-001",
        "binding_affinity": -9.4,
        "residue_count": 188,
        "screened": 12,
        "pareto_count": 3,
        "leads": [
            {
                "id": "LEAD-001",
                "smiles": "O=C(N1CCN(C2=NC=C(Cl)C3=C2C(C4=C(F)C=CC=C4F)=CC=C3)CC1)C5=C(N)N=C6C(F)=CC=CC6=C5",
                "mw": 482.3,
                "logp": 3.1,
                "qed": 0.78,
                "sascore": 2.7,
                "admet_verdict": "PASS"
            }
        ],
        "retrosynthesis": {
            "num_steps": 2,
            "feasibility": "Commercially Accessible (1-2 steps)",
            "steps": [
                {
                    "step": 1,
                    "reaction_type": "Amide Coupling (PyBOP/DIPEA)",
                    "reagents": ["DIPEA", "DMF", "rt 2h"],
                    "yield_pct": 84.0,
                    "difficulty": "Routine (★☆☆)"
                },
                {
                    "step": 2,
                    "reaction_type": "Suzuki-Miyaura Cross-Coupling",
                    "reagents": ["Pd(dppf)Cl2", "K2CO3", "80°C"],
                    "yield_pct": 78.0,
                    "difficulty": "Routine (★☆☆)"
                }
            ]
        }
    }

    pdf_bytes = generate_ind_pdf(sample_dossier)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


def test_api_ind_dossier_pdf_endpoint(client):
    """Verify POST /api/dossier/pdf returns PDF with correct HTTP headers."""
    resp = client.post("/api/dossier/pdf", json={
        "dossier": {
            "target": "EGFR T790M",
            "nominated_lead": "LEAD-042",
            "binding_affinity": -8.9
        }
    })
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment; filename=" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF-")


# ==============================================================================
# Feature 3: Opentrons OT-2 Robot Protocol Tests
# ==============================================================================
def test_ot2_protocol_code_syntax():
    """Verify generated Opentrons Python protocol parses cleanly as valid Python AST."""
    plan = RetrosynthesisPlan(
        candidate_id="LEAD-001",
        target_smiles="CC(=O)Nc1ccc(O)cc1",
        num_steps=2,
        overall_feasibility="Commercially Accessible (1-2 steps)",
        steps=[
            RetrosynthesisStep(
                step_number=1,
                reaction_type="Amide Condensation",
                reaction_smarts="",
                reactants=[{"name": "4-aminophenol"}],
                reagents=["Ac2O", "AcOH"],
                product_smiles="CC(=O)Nc1ccc(O)cc1",
                estimated_yield_pct=90.0,
                difficulty="Routine (★☆☆)"
            )
        ],
        starting_materials=["4-aminophenol (CAS 123-30-8)", "Acetic anhydride"],
        estimated_turnaround_days=2
    )

    py_code = generate_ot2_protocol(plan)
    assert "metadata" in py_code
    assert "protocol_api.ProtocolContext" in py_code
    assert "opentrons_96_tiprack_300ul" in py_code
    assert "temperature module gen2" in py_code
    
    # Must parse without syntax errors
    parsed_ast = ast.parse(py_code)
    assert isinstance(parsed_ast, ast.Module)


def test_lab_card_markdown():
    """Verify wet-lab SOP card generates formatted markdown with safety instructions."""
    plan = RetrosynthesisPlan(
        candidate_id="LEAD-002",
        target_smiles="c1ccccc1",
        num_steps=1,
        overall_feasibility="Routine",
        steps=[
            RetrosynthesisStep(
                step_number=1,
                reaction_type="Hydrogenation",
                reaction_smarts="",
                reactants=[{"name": "Benzene"}],
                reagents=["H2", "Pd/C"],
                product_smiles="C1CCCCC1",
                estimated_yield_pct=95.0,
                difficulty="Routine"
            )
        ],
        starting_materials=["Benzene (CAS 71-43-2)"],
        estimated_turnaround_days=1
    )

    card = generate_lab_card(plan, "LEAD-002")
    assert "# 🧪 Wet-Lab Protocol Card — LEAD-002" in card
    assert "Starting Materials Required" in card
    assert "Opentrons OT-2" in card


def test_api_robot_protocol_endpoint(client):
    """Verify POST /api/robot/protocol endpoint returns protocol and SOP."""
    resp = client.post("/api/robot/protocol", json={
        "lead_id": "LEAD-777",
        "smiles": "CC(=O)N1CCNCC1",
        "retrosynthesis": {
            "num_steps": 2,
            "feasibility": "Custom Multi-Step",
            "steps": [
                {"step": 1, "reaction_type": "Buchwald-Hartwig Amination", "yield_pct": 72.0}
            ]
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["candidate_id"] == "LEAD-777"
    assert "opentrons" in data["ot2_protocol_py"]
    assert "Wet-Lab Protocol Card" in data["lab_card_md"]


# ==============================================================================
# Feature 1: Adaptive Resistance Escape Engine Tests
# ==============================================================================
def test_resistance_escape_engine_scan():
    """Verify resistance engine detects mutational collapse and evolves counter-design."""
    engine = ResistanceEscapeEngine(mock=True)
    
    lead = MoleculeCandidate(
        id="LEAD-TEST",
        smiles="O=C(N1CCN(C2=NC=C(Cl)C3=C2C(C4=C(F)C=CC=C4F)=CC=C3)CC1)C5=C(N)N=C6C(F)=CC=CC6=C5",
        parent_smiles="",
        binding_affinity=-9.4
    )
    target = TargetProfile(
        name="KRAS G12D",
        gene="KRAS",
        uniprot_id="P01116",
        pdb_id="8AZV",
        description="Oncogenic KRAS G12D",
        canonical_sequence="MTEYKLVVVGAGDVGKSALTIQLIQNHFVDE",
        pocket_residues=["Gly12", "Asp12", "Tyr96", "Gln61"],
        reference_ligand_name="MRTX1133",
        reference_ligand_smiles="CC"
    )

    scan = engine.scan_and_evolve(lead=lead, target=target)
    assert scan.original_lead_id == "LEAD-TEST"
    assert scan.original_affinity == -9.4
    assert scan.resistance_detected is True
    # Mutant affinity must be worse (closer to 0)
    assert scan.mutant_affinity > scan.original_affinity
    # Evolved affinity must be recovered (more negative)
    assert scan.evolved_affinity < scan.mutant_affinity
    assert scan.delta_recovery > 0.0
    assert len(scan.evolved_lead_smiles) > 5


def test_api_resistance_evolve_endpoint(client):
    """Verify POST /api/resistance/evolve endpoint handles requests cleanly."""
    resp = client.post("/api/resistance/evolve", json={
        "target": "EGFR T790M",
        "lead_id": "LEAD-001",
        "smiles": "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1",
        "binding_affinity": -9.1
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["resistance_detected"] is True
    assert "T790M" in data["mutation_simulated"] or "Resistance" in data["mutation_simulated"]
    assert data["delta_recovery"] > 0
    assert data["verdict"] == "RESISTANCE BYPASSED"
