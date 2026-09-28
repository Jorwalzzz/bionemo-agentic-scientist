"""
Agentic BioNeMo - Data Models & Scientific Schemas
Defines structured classes for targets, molecules, docking poses, and agent actions.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import time

@dataclass
class TargetProfile:
    name: str                           # e.g. "KRAS G12D"
    gene: str                           # "KRAS"
    uniprot_id: str                     # "P01116"
    pdb_id: str                         # "8AZV"
    description: str                    # Clinical oncology background
    canonical_sequence: str             # 20 IUPAC amino acid sequence
    pocket_residues: List[str]          # ["Gly12Asp", "Gln61", "Tyr96", "Asp69"]
    reference_ligand_name: str          # "MRTX1133"
    reference_ligand_smiles: str        # Parent chemical scaffold
    target_pocket_coords: Dict[str, float] = field(default_factory=lambda: {"x": 12.4, "y": -4.2, "z": 18.9})

@dataclass
class MoleculeCandidate:
    id: str
    smiles: str
    parent_smiles: str
    molecular_formula: str = ""
    mw: float = 0.0
    logp: float = 0.0
    tpsa: float = 0.0
    hbd: int = 0
    hba: int = 0
    rotatable_bonds: int = 0
    qed: float = 0.0
    sascore: float = 0.0                # Synthetic Accessibility Score (1=easy, 10=hard)
    pains_alerts: List[str] = field(default_factory=list)
    passes_lipinski: bool = True
    passes_veber: bool = True
    bbb_permeable: bool = False
    herg_liability: bool = False        # Cardiac ion channel risk heuristic
    admet_verdict: str = "PENDING"      # "PASS", "FLAGGED", "REJECT"
    admet_notes: List[str] = field(default_factory=list)
    binding_affinity: float = 0.0       # kcal/mol (negative is favorable)
    diffdock_confidence: float = 0.0    # 0.0 to 1.0
    contact_residues: List[str] = field(default_factory=list)
    pose_sdf: str = ""
    is_pareto_optimal: bool = False
    generation_round: int = 1
    composite_rank_score: float = 0.0

@dataclass
class AgentMessage:
    agent_name: str                     # "TargetScout", "GenerativeChemist", "ADMETCritic", "BiophysicsDocking", "PIAgent"
    role: str                           # "Agent", "Critic", "Director"
    action: str                         # e.g., "QUERY_MOLMIM", "CALCULATE_ADMET", "DOCK_DIFFDOCK"
    thought: str                        # Internal reasoning & clinical context
    output_summary: str
    timestamp: float = field(default_factory=time.time)
    status: str = "SUCCESS"             # "SUCCESS", "WARNING", "FAILED"

@dataclass
class DossierReport:
    target: TargetProfile
    top_leads: List[MoleculeCandidate]
    screened_count: int
    passed_admet_count: int
    docked_count: int
    pareto_leads_count: int
    executive_summary: str
    agent_audit_log: List[AgentMessage]
    timestamp: str = ""
