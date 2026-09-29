"""
Unit tests for Universal Target Ingestion (Dr. Cynthia).
"""
from src.target_scout import TargetScoutAgent

def test_preset_target_resolution():
    scout = TargetScoutAgent()
    profile, msg = scout.scout_target("EGFR T790M")
    assert profile.pdb_id == "2ITZ"
    assert len(profile.canonical_sequence) > 100
    assert msg.status == "SUCCESS"

def test_rcsb_pdb_target_resolution():
    scout = TargetScoutAgent()
    profile, msg = scout.scout_target("6LU7")
    assert profile.pdb_id == "6LU7"
    assert len(profile.canonical_sequence) > 100
    assert "6LU7" in msg.output_summary
