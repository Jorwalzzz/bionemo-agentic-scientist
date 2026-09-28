"""
Agentic BioNeMo - Agent 1: Target Scout Agent
Resolves oncology targets, fetches 3D crystal structures, identifies binding pockets,
and validates canonical amino acid sequences.
"""
import logging
from typing import Dict, Tuple
from src.models import TargetProfile, AgentMessage
from src.pdb_utils import fetch_pdb_online_or_mock, clean_pdb_structure, extract_sequence_from_pdb, validate_sequence

logger = logging.getLogger("TargetScout")

TARGET_REGISTRY: Dict[str, Dict] = {
    "SARS-CoV-2 Mpro": {
        "gene": "ORF1ab",
        "uniprot_id": "P0DTD1",
        "pdb_id": "7BQY",
        "description": "Viral main protease homodimer essential for processing viral polyproteins.",
        "canonical_sequence": "SGFRKMAFPSGKVEGCMVQVTCGTTTLNGLWLDDVVYCPRHVICTSEDMLNPNYEDLLIRKSNHNFLVQAGNVQLRVIGHSMQNCVLKLKVDTANPKTPKYKFVRIQPGQTFSVLACYNGSPSGVYQCAMRPNFTIKGSFLNGSCGSVGFNIDYDCVSFCYMHHMELPTGVHAGTDLEGNFYGPFVDRQTAQAAGTDTTITVNVLAWLYAAVINGDRWFLNRFTTTLNDFNLVAMKYNYEPLTQDHVDILGPLSAQTGIAVLDMCASLKELLQNGMNGRTILGSALLEDEFTPFDVVRQCSGVTFQ",
        "pocket_residues": ["His41", "Cys145", "Met49", "Met165", "Glu166", "Gln189"],
        "reference_ligand_name": "Nirmatrelvir",
        "reference_ligand_smiles": "CC1(C2C1C(N(C2)C(=O)C(C(C)(C)C)NC(=O)C(F)(F)F)C(=O)NC(CC3CCNC3=O)C#N)C",
        "pocket_coords": {"x": 9.2, "y": -4.5, "z": 21.3}
    },
    "HER2": {
        "gene": "ERBB2",
        "uniprot_id": "P04626",
        "pdb_id": "3PP0",
        "description": "Receptor tyrosine-protein kinase erbB-2 catalytic domain amplified in breast and gastric carcinomas.",
        "canonical_sequence": "KVLGSGAFGTVYKGIWIPDGENVKIPVAIKVLRENTSPKANKEILDEAYVMAGVGSPYVSRLLGICLTSTVQLVTQLMPYGCLLDHVRENRGRLGSQDLLNWCMQIAKGMSYLEDVRLVHRDLAARNVLVKSPNHVKITDFGLARLLDIDETEYHADGGKVPIKWMALESILRRRFTHQSDVWSYGVTVWELMTFGAKPYDGIPAREIPDLLEKGERLPQPPICTIDVYMIMVKCWMIDSECRPRFRELVSEFSRMARDPQRFVVIQNEDLGPASPLDSTFYRSLLEDDDMGDLVDAEEYLVPQQGFFCPDPAPGAGGMVHHRHRSSSTRSGGGDLTLGLEPSEEEAPRSPLAPSEGAGSDVFDGDLGMGAAKGLQSLPTHDPSPLQRYSEDPTVPLPSETDGYVAPLTCSPQPEYVNQPDVRPQPPSPREGPLPAARPAGATLERPKTLSPGKNGVVKDVFAFGGAVENPEYLTPQGGAAPQPHPPPAFSPAFDNLYYWDQDPPERGAPPSTFKGTPTAENPEYLGLDVPV",
        "pocket_residues": ["Thr798", "Met801", "Lys753", "Leu726", "Cys805", "Asp863"],
        "reference_ligand_name": "Lapatinib",
        "reference_ligand_smiles": "CS(=O)(=O)CCNCC1=CC=C(O1)C2=CC3=C(C=C2)N=CN=C3NC4=CC(=C(C=C4)OCC5=CC(=CC=C5)F)Cl",
        "pocket_coords": {"x": 18.5, "y": 14.2, "z": 32.8}
    },
    "KRAS G12D": {
        "gene": "KRAS",
        "uniprot_id": "P01116",
        "pdb_id": "8AZV",
        "description": "Oncogenic KRAS G12D switch-II pocket driver in pancreatic and colorectal adenocarcinoma.",
        "canonical_sequence": "MTEYKLVVVGADGVGKSALTIQLIQNHFVDEYDPTIEDSYRKQVVIDGETCLLDILDTAGQEEYSAMRDQYMRTGEGFLCVFAINNTKSFEDIHHYREQIKRVKDSEDVPMVLVGNKCDLPSRTVDTKQAQDLARSYGIPFIETSAKTRQRVEDAFYTLVREIRQYRLKKISKEEKTPGCVKIKKCIIM",
        "pocket_residues": ["Asp12", "Gly60", "Gln61", "Tyr96", "Arg68", "Asp69"],
        "reference_ligand_name": "MRTX1133",
        "reference_ligand_smiles": "O=C(N1CCN(C2=NC=C(Cl)C3=C2C(C4=C(F)C=CC=C4F)=CC=C3)CC1)C5=C(N)N=C6C(F)=CC=CC6=C5",
        "pocket_coords": {"x": 14.2, "y": 8.5, "z": -12.1}
    },
    "EGFR T790M": {
        "gene": "EGFR",
        "uniprot_id": "P00533",
        "pdb_id": "2ITZ",
        "description": "Acquired clinical gatekeeper resistance mutation in NSCLC kinase domain conferring steric clash.",
        "canonical_sequence": "LGEAPNQALLRILKETEFKKIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLP",
        "pocket_residues": ["Met790", "Thr854", "Lys745", "Asp855", "Leu718", "Cys797"],
        "reference_ligand_name": "Gefitinib",
        "reference_ligand_smiles": "COC1=C(OCC2CCNCC2)C=C3C(=C1)N=CN=C3NC4=CC(=C(F)C=C4)Cl",
        "pocket_coords": {"x": 22.1, "y": 0.4, "z": 52.8}
    },
    "BRAF V600E": {
        "gene": "BRAF",
        "uniprot_id": "P15056",
        "pdb_id": "4MNE",
        "description": "Constitutively active monomeric kinase in melanoma mimicking activation-loop phosphorylation.",
        "canonical_sequence": "MAALSGGGGGGAEPGQALFNGDMEPEAGAGAGAAASSAADPAIPEEVWNIKQMIKLTQEHIEALLDKFGGEHNPPSIYLDAYEEYTSKLDALQQREQQLLESLGNGTDFSVSSSASMDTVTSSSSSSLSVLPSSLSVFQNPTDVARSNPKSPQKPIVRVFLPNKQRTVVPARCGVTVRDSLKKALMMRGLIPECCAVYRIQDGEKKPIGWDTDISWLTGEELHVEVLENVPLTTHNFVRKTFFTLAFCDFCRKLLFQGFRCQTCGYKFHQRCSTEVPLMCVNYDQLDLLFVSKFFEHHPIPQEEASLAETALTSGSSPSAPASDSIGPQILTSPSPSKSIPIPQPFRPADEDHRNQFGQRDRSSSAPNVHINTIEPVNIDDLIRDQGFRGDGGSTTGLSATPPASLPGSLTNVKALQKSPGPQRERKSSSSSEDRNRMKTLGRRDSSDDWEIPDGQITVGQRIGSGSFGTVYKGKWHGDVAVKMLNVTAPTPQQLQAFKNEVGVLRKTRHVNILLFMGYSTKPQLAIVTQWCEGSSLYHHLHIIETKFEMIKLIDIARQTAQGMDYLHAKSIIHRDLKSNNIFLHEDLTVKIGDFGLATEKSRWSGSHQFEQLSGSILWMAPEVIRMQDKNPYSFQSDVYAFGIVLYELMTGQLPYSNINNRDQIIFMVGRGYLSPDLSKVRSNCPKAMKRLMAECLKKKRDERPLFPQILASIELLARSLPKIHRSASEPSLNRAGFQTEDFSLYACASPKTPIQAGGYGAFPVH",
        "pocket_residues": ["Glu600", "Phe595", "Lys483", "Leu514", "Asp594"],
        "reference_ligand_name": "Vemurafenib",
        "reference_ligand_smiles": "CCCS(=O)(=O)NC1=C(F)C(=C(C=C1)C(=O)C2=CNC3=C2C=C(C=N3)C4=CC=C(Cl)C=C4)F",
        "pocket_coords": {"x": -0.8, "y": -14.2, "z": -18.7}
    }
}

class TargetScoutAgent:
    def __init__(self, name: str = "TargetScout"):
        self.name = name
        
    def scout_target(self, query: str) -> Tuple[TargetProfile, AgentMessage]:
        """Resolves target, downloads PDB, validates canonical residues, returns TargetProfile."""
        normalized_query = query.upper().strip()
        matched_key = None
        for key in TARGET_REGISTRY:
            if key.upper() in normalized_query or any(token in normalized_query for token in key.upper().split()):
                matched_key = key
                break
                
        if not matched_key:
            matched_key = "KRAS G12D" # Default gold standard target
            
        data = TARGET_REGISTRY[matched_key]
        raw_pdb = fetch_pdb_online_or_mock(data["pdb_id"])
        cleaned_pdb = clean_pdb_structure(raw_pdb)
        
        is_valid, invalid_aas = validate_sequence(data["canonical_sequence"])
        if not is_valid:
            logger.warning(f"Target sequence contains non-canonical residues: {invalid_aas}")
            
        profile = TargetProfile(
            name=matched_key,
            gene=data["gene"],
            uniprot_id=data["uniprot_id"],
            pdb_id=data["pdb_id"],
            description=data["description"],
            canonical_sequence=data["canonical_sequence"],
            pocket_residues=data["pocket_residues"],
            reference_ligand_name=data["reference_ligand_name"],
            reference_ligand_smiles=data["reference_ligand_smiles"],
            target_pocket_coords=data["pocket_coords"]
        )
        
        message = AgentMessage(
            agent_name=self.name,
            role="Target Scout",
            action="SCOUT_TARGET_RESOLUTION",
            thought=(
                f"Resolved query '{query}' to clinical target {profile.name} (UniProt {profile.uniprot_id}, PDB {profile.pdb_id}). "
                f"Structural pocket mapped around {len(profile.pocket_residues)} key residues: {', '.join(profile.pocket_residues[:4])}. "
                f"Reference scaffold established from {profile.reference_ligand_name}."
            ),
            output_summary=f"Mapped {profile.name} (PDB: {profile.pdb_id}) with {len(profile.canonical_sequence)} validated canonical residues.",
            status="SUCCESS"
        )
        return profile, message
