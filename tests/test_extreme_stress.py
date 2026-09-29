"""
Extreme Stress & Boundary Test Suite for NVIDIA BioNeMo Platform.
Tests all endpoints, pipeline functions, data models, error handlers, and edge cases.
"""

import os
import sys
import ast
import json
import pytest
from fastapi.testclient import TestClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from serve_cockpit import app
from src.models import (
    MoleculeCandidate, TargetProfile, DossierReport,
    RetrosynthesisPlan, RetrosynthesisStep, ResistanceScan
)
from src.admet_critic import ADMETCriticAgent
from src.generative_chemist import GenerativeChemistAgent
from src.docking_agent import BiophysicsDockingAgent
from src.retrosynthesis_agent import RetrosynthesisAgent
from src.target_scout import TargetScoutAgent
from src.pi_agent import PrincipalInvestigatorAgent
from src.orchestrator import AgenticScientistOrchestrator
from src.resistance_engine import ResistanceEscapeEngine
from src.robot_protocol import generate_ot2_protocol, generate_lab_card
from src.ind_dossier import generate_ind_pdf
from src.pdb_utils import clean_pdb_structure, extract_sequence_from_pdb, resolve_protein_structure


@pytest.fixture
def client():
    return TestClient(app)


class TestExtremeLoop1APIEndpointsAndBoundaryConditions:
    """Loop 1: Test all FastAPI endpoints with boundary, empty, and adversarial payloads."""

    def test_health_and_trial_endpoints(self, client):
        r1 = client.get("/api/health")
        assert r1.status_code == 200
        assert r1.json()["status"] == "healthy"

        r2 = client.get("/api/trial-status")
        assert r2.status_code == 200
        data = r2.json()
        assert "allowed" in data

        r3 = client.post("/api/reset-trial")
        assert r3.status_code == 200
        assert r3.json()["success"] is True

    def test_speedup_benchmark_endpoint(self, client):
        r = client.get("/api/benchmark/speedup")
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "success"
        assert d["overall_speedup_multiplier"] > 10.0
        assert len(d["tasks"]) == 3

    def test_dossier_pdf_endpoint_adversarial(self, client):
        payload = {
            "target": "Synthetic Oncology Target (Loop 1)",
            "nominated_lead": "LEAD-STRESS-999",
            "binding_affinity": -11.5,
            "leads": [
                {
                    "id": "LEAD-STRESS-999",
                    "smiles": "c1ccccc1O",
                    "mw": 94.11,
                    "logp": 1.46,
                    "qed": 0.55,
                    "sascore": 1.1,
                    "admet_verdict": "PASS"
                }
            ],
            "retrosynthesis": {
                "num_steps": 1,
                "feasibility": "Commercial (1-step)",
                "steps": [
                    {
                        "step": 1,
                        "reaction_type": "Phenol Diazotization",
                        "reagents": ["NaNO2", "HCl", "H2O"],
                        "yield_pct": 88.0,
                        "difficulty": "Routine (★☆☆)"
                    }
                ]
            }
        }
        res = client.post("/api/dossier/pdf", json=payload)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert len(res.content) > 1000
        assert res.content.startswith(b"%PDF")

    def test_robot_protocol_endpoint_adversarial(self, client):
        payload = {
            "lead_id": "LEAD-ROBOT-STRESS",
            "lead_smiles": "CC(=O)Nc1ccc(O)cc1",
            "target_name": "Acetaminophen Analogue",
            "synthesis_steps": [
                {
                    "step": 1,
                    "reaction_type": "Acylation",
                    "reagents": ["Acetic anhydride", "Pyridine"],
                    "yield_pct": 95.0,
                    "difficulty": "Routine"
                }
            ]
        }
        res = client.post("/api/robot/protocol", json=payload)
        assert res.status_code == 200
        d = res.json()
        assert d["status"] == "success"
        assert "from opentrons import protocol_api" in d["ot2_protocol_py"]
        # Verify valid AST parse
        parsed = ast.parse(d["ot2_protocol_py"])
        assert parsed is not None

    def test_resistance_evolve_endpoint_adversarial(self, client):
        payload = {
            "target": "KRAS G12D",
            "mutation": "G12D -> G12C (Switch-II Escape)",
            "lead_id": "LEAD-001",
            "baseline_smiles": "O=C(N1CCNCC1)c2ccccc2",
            "baseline_affinity": -9.2
        }
        res = client.post("/api/resistance/evolve", json=payload)
        assert res.status_code == 200
        d = res.json()
        assert d["status"] == "success"
        assert d["delta_recovery"] > 0
        assert "evolved_lead_smiles" in d


class TestExtremeLoop2CheminformaticsAndPDB:
    """Loop 2: PDB parsing, sequence extraction, structure resolution, and sanitization."""

    def test_extract_sequence_and_clean_pdb(self):
        sample_pdb = (
            "HEADER    TEST PROTEIN\n"
            "ATOM      1  N   MET A   1      11.104  13.201  -9.041  1.00 10.00           N\n"
            "ATOM      2  CA  MET A   1      11.104  14.201  -9.041  1.00 10.00           C\n"
            "ATOM      3  C   MET A   1      12.104  14.201  -9.041  1.00 10.00           C\n"
            "ATOM      4  O   MET A   1      12.104  15.201  -9.041  1.00 10.00           O\n"
            "ATOM      5  N   ALA A   2      13.104  14.201  -9.041  1.00 10.00           N\n"
            "ATOM      6  CA  ALA A   2      13.104  15.201  -9.041  1.00 10.00           C\n"
            "ATOM      7  C   ALA A   2      14.104  15.201  -9.041  1.00 10.00           C\n"
            "ATOM      8  O   ALA A   2      14.104  16.201  -9.041  1.00 10.00           O\n"
            "HETATM    9  O   HOH A 101      15.000  15.000  -9.000  1.00 20.00           O\n"
            "END\n"
        )
        seq = extract_sequence_from_pdb(sample_pdb)
        assert seq == "MA"

        cleaned = clean_pdb_structure(sample_pdb, keep_hetero=False)
        assert "HOH" not in cleaned
        assert "MET" in cleaned

    def test_resolve_protein_structure_mock_flow(self):
        pdb_text1 = resolve_protein_structure(pdb_id="8AZV")
        assert "ATOM" in pdb_text1

        pdb_text2 = resolve_protein_structure(sequence="MTEYKLVVVGADGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQ")
        assert "ATOM" in pdb_text2
        assert "CA" in pdb_text2


class TestExtremeLoop3MultiAgentCouncil:
    """Loop 3: Collaborative agent execution, message passing, scoring, and edge cases."""

    def test_all_agents_run_harmoniously(self):
        target_scout = TargetScoutAgent(mock=True)
        gen_chemist = GenerativeChemistAgent(mock=True)
        admet_critic = ADMETCriticAgent()
        docker = BiophysicsDockingAgent(mock=True)
        retro = RetrosynthesisAgent()
        pi_arbiter = PrincipalInvestigatorAgent()

        # Step 1: Scout
        target, scout_msg = target_scout.scout_target("KRAS G12D")
        assert isinstance(target, TargetProfile)
        assert len(target.canonical_sequence) > 10
        assert scout_msg.status == "SUCCESS"

        # Step 2: Generative
        molecules, chem_msg = gen_chemist.generate_derivatives(
            parent_smiles=target.reference_ligand_smiles,
            target_name=target.name,
            num_molecules=4
        )
        assert len(molecules) == 4
        assert isinstance(molecules[0], MoleculeCandidate)
        assert chem_msg.status == "SUCCESS"

        # Step 3: ADMET
        evaluated_mols, critic_msg = admet_critic.evaluate_candidates(molecules)
        assert len(evaluated_mols) == 4
        assert critic_msg.status == "SUCCESS"

        # Step 4: Docking
        docked_mols, dock_msg = docker.dock_candidates(evaluated_mols, target)
        assert len(docked_mols) == 4
        assert docked_mols[0].binding_affinity < 0.0
        assert dock_msg.status == "SUCCESS"

        # Step 5: Retrosynthesis
        retro_plans = [retro.plan_synthesis_route(m) for m in docked_mols]
        assert len(retro_plans) == 4
        assert retro_plans[0].num_steps > 0

        # Step 6: PI Arbiter
        top_leads, pi_msg = pi_arbiter.evaluate_and_rank_leads(docked_mols, target)
        assert len(top_leads) > 0
        assert pi_msg.status == "SUCCESS"


class TestExtremeLoop4ResistanceEngine:
    """Loop 4: Mutation resistance engine stress test across different clinical targets."""

    def test_resistance_stress_test_varieties(self):
        engine = ResistanceEscapeEngine(mock=True)

        target = TargetProfile(
            name="KRAS G12D",
            gene="KRAS",
            uniprot_id="P01116",
            pdb_id="8AZV",
            description="Test target",
            canonical_sequence="MTEYKLVVVGADGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQ",
            pocket_residues=["Gly12Asp", "Gln61"],
            reference_ligand_name="MRTX1133",
            reference_ligand_smiles="CC1=CC=C(C=C1)NC2=NC=C(F)C(=N2)N3CCNCC3"
        )
        lead = MoleculeCandidate(
            id="LEAD-001",
            smiles="CC(=O)Oc1ccccc1C(=O)O",
            parent_smiles="c1ccccc1",
            binding_affinity=-9.2
        )
        scan = engine.scan_and_evolve(lead=lead, target=target)
        assert isinstance(scan, ResistanceScan)
        assert scan.resistance_detected is True
        assert scan.delta_recovery > 0.0
        assert len(scan.evolved_lead_smiles) > 5


class TestExtremeLoop5OrchestratorAndFullCampaign:
    """Loop 5: Full end-to-end campaign execution from target to final dossier."""

    def test_full_autonomous_campaign(self):
        orchestrator = AgenticScientistOrchestrator(mock=True)
        report = orchestrator.run_discovery_campaign(
            target_query="KRAS G12D",
            num_candidates=4
        )
        assert report is not None
        assert isinstance(report, DossierReport)
        assert len(report.top_leads) > 0
        assert report.target.name == "KRAS G12D"
        assert os.path.exists(os.path.join(BASE_DIR, "results", "CANDIDATE_SELECTION_DOSSIER.md"))
        assert os.path.exists(os.path.join(BASE_DIR, "results", "top_leads_docked.sdf"))
