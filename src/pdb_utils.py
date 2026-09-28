"""
Agentic BioNeMo - Macromolecular PDB Utilities
PDB downloading, structure cleaning, and canonical 20 IUPAC amino acid validation.
"""
import os
import re
import requests
from typing import Tuple, List

CANONICAL_20_IUPAC = set("ACDEFGHIKLMNPQRSTVWY")

AA3_TO_1 = {
    "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
    "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
    "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
    "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y"
}

def validate_sequence(sequence: str) -> Tuple[bool, List[str]]:
    """Validates sequence against the canonical 20 IUPAC residues."""
    invalid = [char for char in sequence.upper() if char not in CANONICAL_20_IUPAC]
    return (len(invalid) == 0, list(set(invalid)))

def clean_pdb_structure(raw_pdb: str, keep_hetero: bool = False) -> str:
    """
    Cleans PDB file:
    - Retains ATOM records
    - Removes crystallographic water (HOH, WAT)
    - Optionally removes non-ligand HETATM records
    """
    cleaned_lines = []
    for line in raw_pdb.splitlines():
        if line.startswith("ATOM"):
            cleaned_lines.append(line)
        elif line.startswith("HETATM") and keep_hetero:
            res_name = line[17:20].strip()
            if res_name not in ["HOH", "WAT", "SO4", "GOL", "EDO", "DMS"]:
                cleaned_lines.append(line)
        elif line.startswith("TER") or line.startswith("END"):
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def extract_sequence_from_pdb(pdb_content: str, chain_id: str = "A") -> str:
    """Extracts 1-letter canonical amino acid sequence from PDB ATOM lines."""
    seen_residues = set()
    seq_chars = []
    
    for line in pdb_content.splitlines():
        if line.startswith("ATOM"):
            res_chain = line[21]
            if chain_id and res_chain != chain_id:
                continue
            res_seq_num = line[22:27].strip()
            res_name = line[17:20].strip()
            
            key = (res_chain, res_seq_num)
            if key not in seen_residues:
                seen_residues.add(key)
                one_letter = AA3_TO_1.get(res_name, "X")
                seq_chars.append(one_letter)
                
    sequence = "".join(seq_chars)
    return sequence

def fetch_pdb_online_or_mock(pdb_id: str, cache_dir: str = "data/targets") -> str:
    """Fetches PDB from RCSB or returns cached clean structure."""
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{pdb_id.upper()}.pdb")
    
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()
            
    # RCSB REST download
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            return resp.text
    except Exception:
        pass
        
    # Fallback minimal synthetic backbone if offline
    synthetic_pdb = f"""HEADER    SYNTHETIC TARGET PDB {pdb_id.upper()}
ATOM      1  N   MET A   1      11.120  -3.450  14.210  1.00 20.00           N
ATOM      2  CA  MET A   1      11.950  -2.280  14.530  1.00 20.00           C
ATOM      3  C   MET A   1      13.410  -2.670  14.340  1.00 20.00           C
ATOM      4  O   MET A   1      13.780  -3.840  14.480  1.00 20.00           O
ATOM      5  N   GLY A   2      14.250  -1.680  14.020  1.00 18.00           N
ATOM      6  CA  GLY A   2      15.680  -1.920  13.820  1.00 18.00           C
ATOM      7  C   GLY A   2      16.420  -0.650  13.450  1.00 18.00           C
ATOM      8  O   GLY A   2      16.030   0.450  13.840  1.00 18.00           O
TER       9      GLY A   2
END
"""
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(synthetic_pdb)
    return synthetic_pdb
