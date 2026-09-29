"""
Unit tests for NVIDIA BioNeMo MCP server tools.
"""

import sys
from pathlib import Path
import pytest

# Ensure .agents/tools and project root are importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".agents" / "tools"))
sys.path.insert(0, str(PROJECT_ROOT))

# Gracefully skip in environments where mcp is not installed
pytest.importorskip("mcp")

from bionemo_mcp_server import (
    bionemo_validate_sequence,
    bionemo_sanitize_smiles,
    bionemo_query_esm2_embedding,
    bionemo_query_diffdock,
    bionemo_query_esmfold,
    bionemo_compare_known_inhibitors,
    bionemo_fetch_rcsb_pdb,
)


class TestBionemoMcpTools:
    def test_validate_sequence(self):
        res = bionemo_validate_sequence("MTEYKLVVVGAGGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQ")
        assert res["valid"] is True
        assert res["length"] == 61
        assert "M" in res["residue_counts"]

    def test_sanitize_smiles(self):
        res = bionemo_sanitize_smiles("CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5")
        assert res["valid"] is True
        assert res["canonical_smiles"] is not None
        assert res["molecular_weight"] > 400

    def test_query_esmfold_mock(self):
        res = bionemo_query_esmfold("MTEYKLVVVGAGGVGKSALTIQLIQ", mock=True)
        assert res["model"] == "meta/esmfold"
        assert res["is_mock"] is True
        assert res["mean_plddt"] > 80.0

    def test_compare_known_inhibitors(self):
        res = bionemo_compare_known_inhibitors("EGFR", -9.5)
        assert res["found"] is True
        assert len(res["clinical_reference_benchmarks"]) >= 2
        assert "comparison" in res
        assert res["comparison"]["affinity_delta_kcal_mol"] < 0

    def test_compare_unknown_target(self):
        res = bionemo_compare_known_inhibitors("XYZ999")
        assert res["found"] is False
        assert "available_targets" in res

    def test_fetch_rcsb_pdb_validation(self):
        res = bionemo_fetch_rcsb_pdb("INVALID_ID_TOO_LONG")
        assert res["valid"] is False
