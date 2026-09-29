"""
Unit tests for ESMFold Sequence-to-Structure prediction and 3D visualization payloads.
Part of NVIDIA BioNeMo Agentic Scientist Suite.
Copyright (C) 2026 Jorwalzzz.
"""

import pytest
from src.target_scout import TargetScoutAgent
from src.models import TargetProfile

def test_amino_acid_sequence_detection():
    # Valid sequences
    seq1 = "MTEYKLVVVGAGDVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEE"
    fasta_seq = ">TargetSequence\nMTEYKLVVVGAGDVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVID"
    
    assert TargetScoutAgent.is_amino_acid_sequence(seq1) is True
    assert TargetScoutAgent.is_amino_acid_sequence(fasta_seq) is True
    
    # Invalid or standard names
    assert TargetScoutAgent.is_amino_acid_sequence("KRAS G12D") is False
    assert TargetScoutAgent.is_amino_acid_sequence("6OIM") is False
    assert TargetScoutAgent.is_amino_acid_sequence("NOT_A_SEQUENCE_123!") is False
    assert TargetScoutAgent.is_amino_acid_sequence("ACD") is False # Too short

def test_esmfold_sequence_folding():
    scout = TargetScoutAgent(mock=True)
    seq = "MTEYKLVVVGAGDVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHHYREQIKRVKDSEDVPMVLVGNKCDLPSRTVDTKQAQDLARSYGIPFIETSAKTRQRVEDAFYTLVREIRQYRLKKISKEEKTPGCVKIKKCIIM"
    
    profile, msg = scout.fold_sequence_with_esmfold(seq, target_name="ESMFold: Test Target")
    
    assert isinstance(profile, TargetProfile)
    assert profile.is_esmfold is True
    assert profile.mean_plddt > 70.0
    assert len(profile.pdb_text) > 1000
    assert "ATOM  " in profile.pdb_text
    assert len(profile.pocket_residues) > 0
    assert msg.agent_name == "TargetScout"
    assert "ESMFold" in msg.output_summary or "ESMFold" in msg.thought

def test_scout_target_auto_routes_sequence():
    scout = TargetScoutAgent(mock=True)
    seq = "MTEYKLVVVGAGDVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAM"
    
    profile, msg = scout.scout_target(seq)
    assert profile.is_esmfold is True
    assert profile.mean_plddt > 0.0
    assert len(profile.pdb_text) > 500
