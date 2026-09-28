"""Unit tests for macromolecular PDB parsing and sequence validation."""
import pytest
from src.pdb_utils import validate_sequence, clean_pdb_structure, extract_sequence_from_pdb, fetch_pdb_online_or_mock

def test_validate_canonical_sequence():
    valid_seq = "ACDEFGHIKLMNPQRSTVWY"
    is_valid, invalid = validate_sequence(valid_seq)
    assert is_valid is True
    assert len(invalid) == 0

    invalid_seq = "ACDEFGHIKLMNPQRSTVWYXBZ"
    is_valid, invalid = validate_sequence(invalid_seq)
    assert is_valid is False
    assert "X" in invalid
    assert "B" in invalid
    assert "Z" in invalid

def test_clean_pdb_structure():
    raw = """ATOM      1  N   MET A   1      11.120  -3.450  14.210  1.00 20.00           N
HETATM   99  O   HOH A 101      15.000  -4.000  12.000  1.00 25.00           O
ATOM      2  CA  MET A   1      11.950  -2.280  14.530  1.00 20.00           C
TER       3      MET A   1
"""
    cleaned = clean_pdb_structure(raw)
    assert "HOH" not in cleaned
    assert "ATOM      1  N" in cleaned
    assert "ATOM      2  CA" in cleaned

def test_extract_sequence():
    pdb_snippet = """ATOM      1  N   MET A   1      11.120  -3.450  14.210  1.00 20.00           N
ATOM      2  CA  MET A   1      11.950  -2.280  14.530  1.00 20.00           C
ATOM      3  N   GLY A   2      14.250  -1.680  14.020  1.00 18.00           N
ATOM      4  CA  GLY A   2      15.680  -1.920  13.820  1.00 18.00           C
TER
"""
    seq = extract_sequence_from_pdb(pdb_snippet)
    assert seq == "MG"
