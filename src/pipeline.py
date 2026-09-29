"""
BioNeMo & NIM Inference Benchmark Orchestrator Pipeline.

Coordinates the end-to-end bioinformatics workflow:
1. Protein sequence extraction and validation.
2. Small-molecule ligand sanitization, valency verification, and descriptor calculation via RDKit.
3. High-throughput residue embedding generation via NVIDIA NIM ESM-2 REST endpoints.
4. Baseline CPU unaccelerated embedding benchmark with facebook/esm2_t6_8M_UR50D.
5. Molecular docking pose generation and affinity scoring via NVIDIA NIM DiffDock endpoint.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

from src.client import NimBioClient, ESM2Response, DiffDockResponse
from src.baseline import LocalCPUBaseline, BaselineProfileResult
from src.pdb_utils import resolve_protein_structure

logger = logging.getLogger(__name__)


@dataclass
class LigandValidationResult:
    """Chemical validation and property extraction results from RDKit."""
    raw_smiles: str
    canonical_smiles: str
    is_valid: bool
    error_message: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    log_p: Optional[float] = None
    num_hbd: Optional[int] = None
    num_hba: Optional[int] = None
    tpsa: Optional[float] = None
    num_rotatable_bonds: Optional[int] = None


@dataclass
class ComplexBenchmarkRecord:
    """Consolidated benchmark evaluation record for a single protein-ligand complex."""
    complex_id: str
    target_name: str
    uniprot_id: str
    residue_count: int
    drug_name: str
    drug_indication: str

    # Ligand chemistry
    ligand_validation: LigandValidationResult

    # NIM ESM-2 metrics
    nim_total_latency_ms: float
    nim_server_inference_ms: float
    nim_network_overhead_ms: float
    nim_ms_per_residue: float
    nim_tokens_per_sec: float
    nim_hidden_dim: int
    nim_is_mock: bool

    # CPU Baseline metrics
    cpu_tokenization_ms: float
    cpu_forward_pass_ms: float
    cpu_total_latency_ms: float
    cpu_ms_per_residue: float
    cpu_tokens_per_sec: float
    cpu_peak_memory_mb: float
    cpu_tensor_shape: str
    cpu_is_mock: bool

    # Comparative analysis
    speedup_factor: float
    throughput_improvement_ratio: float

    # NIM DiffDock metrics
    diffdock_latency_ms: float
    diffdock_poses_count: int
    diffdock_top_affinity_kcal_mol: float
    diffdock_top_confidence: float
    diffdock_is_mock: bool

    def to_dict(self) -> Dict[str, Any]:
        """Converts the record into a flat dictionary suitable for Pandas DataFrame export."""
        return {
            "complex_id": self.complex_id,
            "target_name": self.target_name,
            "uniprot_id": self.uniprot_id,
            "residue_count": self.residue_count,
            "drug_name": self.drug_name,
            "drug_indication": self.drug_indication,
            "is_smiles_valid": self.ligand_validation.is_valid,
            "canonical_smiles": self.ligand_validation.canonical_smiles,
            "molecular_formula": self.ligand_validation.molecular_formula,
            "molecular_weight": self.ligand_validation.molecular_weight,
            "log_p": self.ligand_validation.log_p,
            "tpsa": self.ligand_validation.tpsa,
            "nim_total_latency_ms": self.nim_total_latency_ms,
            "nim_server_inference_ms": self.nim_server_inference_ms,
            "nim_network_overhead_ms": self.nim_network_overhead_ms,
            "nim_ms_per_residue": self.nim_ms_per_residue,
            "nim_tokens_per_sec": self.nim_tokens_per_sec,
            "nim_hidden_dim": self.nim_hidden_dim,
            "nim_is_mock": self.nim_is_mock,
            "cpu_tokenization_ms": self.cpu_tokenization_ms,
            "cpu_forward_pass_ms": self.cpu_forward_pass_ms,
            "cpu_total_latency_ms": self.cpu_total_latency_ms,
            "cpu_ms_per_residue": self.cpu_ms_per_residue,
            "cpu_tokens_per_sec": self.cpu_tokens_per_sec,
            "cpu_peak_memory_mb": self.cpu_peak_memory_mb,
            "cpu_tensor_shape": self.cpu_tensor_shape,
            "cpu_is_mock": self.cpu_is_mock,
            "speedup_factor": self.speedup_factor,
            "throughput_improvement_ratio": self.throughput_improvement_ratio,
            "diffdock_latency_ms": self.diffdock_latency_ms,
            "diffdock_poses_count": self.diffdock_poses_count,
            "diffdock_top_affinity_kcal_mol": self.diffdock_top_affinity_kcal_mol,
            "diffdock_top_confidence": self.diffdock_top_confidence,
            "diffdock_is_mock": self.diffdock_is_mock,
        }


class BenchmarkPipeline:
    """
    End-to-end benchmark execution engine comparing NVIDIA NIM microservices
    against local unaccelerated CPU baselines.
    """

    def __init__(
        self,
        nim_client: Optional[NimBioClient] = None,
        cpu_baseline: Optional[LocalCPUBaseline] = None,
        mock: bool = False,
        api_key: Optional[str] = None,
    ):
        self.client = nim_client or NimBioClient(api_key=api_key, mock=mock)
        self.baseline = cpu_baseline or LocalCPUBaseline(mock_fallback=True)

    @staticmethod
    def sanitize_ligand_smiles(smiles: str) -> LigandValidationResult:
        """
        Parses, validates, and sanitizes small-molecule SMILES via RDKit.
        Performs Kekulization and valency integrity checking, and computes
        key physicochemical descriptors.
        """
        if not smiles or not isinstance(smiles, str) or not smiles.strip():
            return LigandValidationResult(
                raw_smiles=str(smiles),
                canonical_smiles="",
                is_valid=False,
                error_message="Empty or non-string SMILES string provided.",
            )

        raw = smiles.strip()
        try:
            # Parse SMILES without sanitizing first to isolate parsing vs valence errors
            mol = Chem.MolFromSmiles(raw, sanitize=False)
            if mol is None:
                return LigandValidationResult(
                    raw_smiles=raw,
                    canonical_smiles="",
                    is_valid=False,
                    error_message="RDKit failed to parse chemical graph from SMILES.",
                )

            # Strict chemical sanitization (valency, aromaticity, kekulization)
            sanitize_ops = Chem.SanitizeFlags.SANITIZE_ALL
            Chem.SanitizeMol(mol, sanitizeOps=sanitize_ops)

            canonical_smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
            formula = rdMolDescriptors.CalcMolFormula(mol)
            mw = round(Descriptors.ExactMolWt(mol), 2)
            logp = round(Descriptors.MolLogP(mol), 2)
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            tpsa = round(Descriptors.TPSA(mol), 2)
            rot_bonds = Descriptors.NumRotatableBonds(mol)

            return LigandValidationResult(
                raw_smiles=raw,
                canonical_smiles=canonical_smiles,
                is_valid=True,
                error_message=None,
                molecular_formula=formula,
                molecular_weight=mw,
                log_p=logp,
                num_hbd=hbd,
                num_hba=hba,
                tpsa=tpsa,
                num_rotatable_bonds=rot_bonds,
            )

        except Exception as e:
            logger.warning("RDKit validation failed for SMILES '%s': %s", raw, str(e))
            return LigandValidationResult(
                raw_smiles=raw,
                canonical_smiles="",
                is_valid=False,
                error_message=str(e),
            )

    def evaluate_complex(
        self,
        sample: Dict[str, Any],
        benchmark_runs: int = 2,
    ) -> ComplexBenchmarkRecord:
        """
        Processes a single complex through all 5 workflow stages:
        1. Sequence & SMILES sanitization
        2. NIM ESM-2 embedding generation
        3. CPU Baseline ESM-2 benchmark
        4. NIM DiffDock docking pose prediction
        5. Metric integration & speedup computation
        """
        complex_id = sample.get("id", "unknown_id")
        target_name = sample.get("target_name", "Target")
        uniprot_id = sample.get("uniprot_id", "N/A")
        sequence = sample.get("sequence", "")
        drug_name = sample.get("drug_name", "Unknown Drug")
        drug_indication = sample.get("drug_indication", "N/A")
        raw_smiles = sample.get("smiles", "")

        logger.info("Evaluating [%s] %s (%d aa) with %s", complex_id, target_name, len(sequence), drug_name)

        # 1. RDKit Sanitization
        ligand_val = self.sanitize_ligand_smiles(raw_smiles)
        if not ligand_val.is_valid:
            logger.warning("Complex %s ligand failed sanitization: %s", complex_id, ligand_val.error_message)

        # 2. NVIDIA NIM ESM-2 Embeddings
        nim_esm_resp: ESM2Response = self.client.get_esm2_embeddings(sequence)
        seq_len = nim_esm_resp.sequence_length
        nim_ms_per_res = nim_esm_resp.latency.total_latency_ms / max(1, seq_len)
        nim_tokens_sec = (seq_len / (nim_esm_resp.latency.total_latency_ms / 1000.0)) if nim_esm_resp.latency.total_latency_ms > 0 else 0.0

        # 3. Local CPU Baseline Benchmark
        cpu_baseline_res: BaselineProfileResult = self.baseline.benchmark_sequence(
            sequence=sequence,
            warmup_runs=1,
            benchmark_runs=benchmark_runs,
        )

        # Speedup computations (Baseline CPU vs NIM GPU)
        speedup = (
            cpu_baseline_res.total_cpu_latency_ms / max(0.001, nim_esm_resp.latency.total_latency_ms)
            if nim_esm_resp.latency.total_latency_ms > 0
            else 1.0
        )
        throughput_ratio = (
            nim_tokens_sec / max(0.001, cpu_baseline_res.tokens_per_sec)
            if cpu_baseline_res.tokens_per_sec > 0
            else 1.0
        )

        # 4. NVIDIA NIM DiffDock Pose Prediction
        active_smiles = ligand_val.canonical_smiles if ligand_val.is_valid else raw_smiles
        pdb_id = sample.get("pdb_id", "")
        try:
            pdb_content = resolve_protein_structure(pdb_id=pdb_id, sequence=sequence)
        except Exception as e:
            logger.warning("Could not resolve PDB structure for %s: %s", complex_id, e)
            pdb_content = None

        diffdock_resp: DiffDockResponse = self.client.dock_complex(
            protein_sequence=sequence,
            ligand_smiles=active_smiles,
            protein_pdb=pdb_content,
            num_poses=5,
        )

        top_conf = diffdock_resp.poses[0].confidence_score if diffdock_resp.poses else 0.0

        return ComplexBenchmarkRecord(
            complex_id=complex_id,
            target_name=target_name,
            uniprot_id=uniprot_id,
            residue_count=seq_len,
            drug_name=drug_name,
            drug_indication=drug_indication,
            ligand_validation=ligand_val,
            nim_total_latency_ms=nim_esm_resp.latency.total_latency_ms,
            nim_server_inference_ms=nim_esm_resp.latency.server_inference_ms,
            nim_network_overhead_ms=nim_esm_resp.latency.network_overhead_ms,
            nim_ms_per_residue=round(nim_ms_per_res, 4),
            nim_tokens_per_sec=round(nim_tokens_sec, 2),
            nim_hidden_dim=nim_esm_resp.hidden_dim,
            nim_is_mock=nim_esm_resp.is_mock,
            cpu_tokenization_ms=cpu_baseline_res.tokenization_ms,
            cpu_forward_pass_ms=cpu_baseline_res.forward_pass_ms,
            cpu_total_latency_ms=cpu_baseline_res.total_cpu_latency_ms,
            cpu_ms_per_residue=cpu_baseline_res.ms_per_residue,
            cpu_tokens_per_sec=cpu_baseline_res.tokens_per_sec,
            cpu_peak_memory_mb=cpu_baseline_res.peak_memory_mb,
            cpu_tensor_shape=str(cpu_baseline_res.tensor_shape),
            cpu_is_mock=cpu_baseline_res.is_mock,
            speedup_factor=round(speedup, 2),
            throughput_improvement_ratio=round(throughput_ratio, 2),
            diffdock_latency_ms=diffdock_resp.latency.total_latency_ms,
            diffdock_poses_count=diffdock_resp.num_poses,
            diffdock_top_affinity_kcal_mol=diffdock_resp.top_affinity_kcal_mol,
            diffdock_top_confidence=top_conf,
            diffdock_is_mock=diffdock_resp.is_mock,
        )

    def run_suite(
        self,
        samples: List[Dict[str, Any]],
        benchmark_runs: int = 2,
    ) -> List[ComplexBenchmarkRecord]:
        """Runs the benchmark pipeline across a list of target complexes."""
        records: List[ComplexBenchmarkRecord] = []
        for sample in samples:
            record = self.evaluate_complex(sample, benchmark_runs=benchmark_runs)
            records.append(record)
        return records
