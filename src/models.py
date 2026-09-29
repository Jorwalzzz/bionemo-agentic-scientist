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
    pdb_text: str = ""                  # Full PDB coordinate string for 3D visualization
    is_esmfold: bool = False            # True if folded de novo via NVIDIA NIM ESMFold
    mean_plddt: float = 0.0             # Per-residue confidence metric (0-100%)

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

@dataclass
class CouncilMessage:
    agent_id: str                       # "scout", "chemist", "critic", "docker", "retro", "pi", "user"
    persona_name: str                   # e.g., "Dr. Marcus (MedChem Critic)"
    avatar: str                         # "⚖️", "🧪", "🎯", "⚡", "🔬", "👑", "👨‍🔬"
    intent: str                         # "PROPOSAL", "VETO", "COUNTER_PROPOSAL", "CLEARANCE", "DOCKING_RESULT", "CONSENSUS", "USER_DIRECTIVE"
    content: str                        # Rich scientific dialogue
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    timestamp_str: str = ""

@dataclass
class RetrosynthesisStep:
    step_number: int
    reaction_type: str                  # e.g. "Suzuki-Miyaura Coupling", "Amide Condensation"
    reaction_smarts: str
    reactants: List[Dict[str, str]]     # [{"name": "...", "smiles": "...", "cas": "..."}]
    reagents: List[str]                 # ["HATU", "DIPEA", "DMF", "rt, 2h"]
    product_smiles: str
    estimated_yield_pct: float
    difficulty: str                     # "Routine (★☆☆)", "Moderate (★★☆)", "Challenging (★★★)"

@dataclass
class RetrosynthesisPlan:
    candidate_id: str
    target_smiles: str
    num_steps: int
    overall_feasibility: str            # "Commercially Accessible (1-2 steps)", "Custom Multi-Step"
    steps: List[RetrosynthesisStep] = field(default_factory=list)
    starting_materials: List[str] = field(default_factory=list)
    estimated_turnaround_days: int = 7

@dataclass
class SafetyRadarScore:
    candidate_id: str
    binding_potency_pct: float          # 0-100 scale
    drug_likeness_qed_pct: float        # 0-100 scale
    synthetic_feasibility_pct: float    # 0-100 scale
    cns_bbb_permeability_pct: float     # 0-100 scale
    cardiac_herg_safety_pct: float      # 0-100 scale
    clinical_selectivity_pct: float     # 0-100 scale
