"""Unit tests for individual agents in the discovery system."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.target_scout import TargetScoutAgent
from src.generative_chemist import GenerativeChemistAgent
from src.admet_critic import ADMETCriticAgent
from src.docking_agent import BiophysicsDockingAgent
from src.pi_agent import PrincipalInvestigatorAgent
from src.models import MoleculeCandidate

def test_target_scout_kras():
    scout = TargetScoutAgent()
    profile, msg = scout.scout_target("KRAS G12D")
    assert profile.name == "KRAS G12D"
    assert profile.gene == "KRAS"
    assert profile.pdb_id == "8AZV"
    assert "Asp12" in profile.pocket_residues
    assert msg.status == "SUCCESS"

def test_target_scout_braf_and_scaffolds():
    scout = TargetScoutAgent()
    profile, msg = scout.scout_target("BRAF V600E")
    assert profile.gene == "BRAF"
    assert profile.pdb_id == "4MNE"
    
    chemist = GenerativeChemistAgent(mock=True)
    cands, cmsg = chemist.generate_derivatives(profile.reference_ligand_smiles, profile.name, num_molecules=10)
    assert len(cands) == 10
    
    critic = ADMETCriticAgent()
    eval_cands, amsg = critic.evaluate_candidates(cands)
    assert len(eval_cands) == 10
    # Confirm no malformed SMILES parse crashes occurred
    valid_count = sum(1 for c in eval_cands if c.admet_verdict in ("PASS", "FLAGGED"))
    assert valid_count > 0

def test_generative_chemist():
    chemist = GenerativeChemistAgent(mock=True)
    parent_smi = "O=C(N1CCN(C2=NC=C(Cl)C3=C2C(C4=C(F)C=CC=C4F)=CC=C3)CC1)C5=C(N)N=C6C(F)=CC=CC6=C5"
    candidates, msg = chemist.generate_derivatives(parent_smi, "KRAS G12D", num_molecules=5)
    assert len(candidates) >= 5
    assert candidates[0].parent_smiles == parent_smi
    assert msg.status == "SUCCESS"

def test_admet_critic_evaluation():
    critic = ADMETCriticAgent()
    # Test valid drug-like molecule
    valid_cand = MoleculeCandidate(
        id="TEST-01",
        smiles="COC1=C(OCC2CCNCC2)C=C3C(=C1)N=CN=C3NC4=CC(=C(F)C=C4)Cl",
        parent_smiles=""
    )
    # Test PAINS quinone molecule
    pains_cand = MoleculeCandidate(
        id="PAINS-01",
        smiles="O=C1C=CC(=O)C=C1",
        parent_smiles=""
    )
    evaluated, msg = critic.evaluate_candidates([valid_cand, pains_cand])
    
    assert evaluated[0].admet_verdict in ("PASS", "FLAGGED")
    assert evaluated[0].mw > 400
    assert evaluated[0].qed > 0.4
    
    assert evaluated[1].admet_verdict == "REJECT"
    assert "Quinone" in evaluated[1].pains_alerts

def test_docking_and_pi_pareto():
    scout = TargetScoutAgent()
    profile, _ = scout.scout_target("KRAS G12D")
    
    cands = [
        MoleculeCandidate(id="C1", smiles="COC1=C(OCC2CCNCC2)C=C3C(=C1)N=CN=C3NC4=CC(=C(F)C=C4)Cl", parent_smiles=""),
        MoleculeCandidate(id="C2", smiles="CC1=C(OCC2CCNCC2)C=C3C(=C1)N=CN=C3NC4=CC(=C(F)C=C4)Cl", parent_smiles="")
    ]
    critic = ADMETCriticAgent()
    eval_cands, _ = critic.evaluate_candidates(cands)
    
    docking = BiophysicsDockingAgent(mock=True)
    docked, _ = docking.dock_candidates(eval_cands, profile)
    assert len(docked) == 2
    assert docked[0].binding_affinity < 0
    assert len(docked[0].pose_sdf) > 0
    
    pi = PrincipalInvestigatorAgent()
    top_leads, _ = pi.evaluate_and_rank_leads(docked, profile)
    assert len(top_leads) > 0
    assert any(c.is_pareto_optimal for c in top_leads)
    assert hasattr(top_leads[0], "composite_rank_score")
    assert top_leads[0].composite_rank_score > 0

def test_target_scout_mpro_and_her2():
    scout = TargetScoutAgent()
    chemist = GenerativeChemistAgent(mock=True)
    critic = ADMETCriticAgent()

    # Test Mpro
    mpro_profile, mpro_msg = scout.scout_target("SARS-CoV-2 Mpro")
    assert mpro_profile.gene == "ORF1ab"
    assert mpro_profile.pdb_id == "7BQY"
    assert "Cys145" in mpro_profile.pocket_residues
    mpro_cands, _ = chemist.generate_derivatives(mpro_profile.reference_ligand_smiles, mpro_profile.name, num_molecules=6)
    assert len(mpro_cands) >= 6
    eval_mpro, _ = critic.evaluate_candidates(mpro_cands)
    assert all(c.qed > 0 for c in eval_mpro)

    # Test HER2
    her2_profile, her2_msg = scout.scout_target("HER2")
    assert her2_profile.gene == "ERBB2"
    assert her2_profile.pdb_id == "3PP0"
    assert "Thr798" in her2_profile.pocket_residues
    her2_cands, _ = chemist.generate_derivatives(her2_profile.reference_ligand_smiles, her2_profile.name, num_molecules=6)
    assert len(her2_cands) >= 6
    eval_her2, _ = critic.evaluate_candidates(her2_cands)
    assert all(c.admet_verdict in ("PASS", "FLAGGED") for c in eval_her2)
