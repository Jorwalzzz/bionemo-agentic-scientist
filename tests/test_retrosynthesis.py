"""
Unit tests for the Retrosynthesis Planner Agent (Dr. Chen).
"""
from src.retrosynthesis_agent import RetrosynthesisAgent
from src.models import MoleculeCandidate

def test_retrosynthesis_amide_coupling():
    agent = RetrosynthesisAgent()
    # Paracetamol / Acetaminophen (contains amide)
    cand = MoleculeCandidate("LEAD-AMIDE", "CC(=O)Nc1ccc(O)cc1", "")
    plan = agent.plan_synthesis_route(cand)

    assert plan.num_steps >= 1
    assert "Amide" in plan.steps[0].reaction_type
    assert len(plan.starting_materials) >= 1
    assert plan.steps[0].estimated_yield_pct > 70.0

def test_retrosynthesis_biaryl_coupling():
    agent = RetrosynthesisAgent()
    # 2-phenylpyridine (contains bi-aryl bond)
    cand = MoleculeCandidate("LEAD-BIARYL", "c1ccc(-c2ccccn2)cc1", "")
    plan = agent.plan_synthesis_route(cand)

    assert plan.num_steps >= 1
    assert any("Suzuki" in s.reaction_type for s in plan.steps)
