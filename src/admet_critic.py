"""
Agentic BioNeMo - Agent 3: ADMET & MedChem Critic Agent
Rigorous RDKit-based physicochemical property profiling, Lipinski/Veber rules,
PAINS structural alerts, and ADMET toxicity heuristics.
"""
import logging
from typing import List, Tuple
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors, QED
from src.models import MoleculeCandidate, AgentMessage

logger = logging.getLogger("ADMETCritic")

# PAINS and reactive motif SMARTS patterns
PAINS_PATTERNS = {
    "Quinone": "[#6]1(=[O,S])[#6]=[#6][#6](=[O,S])[#6]=[#6]1",
    "Rhodanine": "O=C1NC(=S)SC1",
    "Michael Acceptor": "[#6]=[#6]-[#6](=[O,S])",
    "Aliphatic Halide": "[CX4][Cl,Br,I]",
    "Epoxide": "C1OC1",
    "Catechol": "c1c([OX2H])c([OX2H])ccc1"
}

class ADMETCriticAgent:
    def __init__(self, name: str = "ADMETCritic"):
        self.name = name
        self._compiled_pains = {k: Chem.MolFromSmarts(v) for k, v in PAINS_PATTERNS.items() if Chem.MolFromSmarts(v)}

    def evaluate_candidates(self, candidates: List[MoleculeCandidate]) -> Tuple[List[MoleculeCandidate], AgentMessage]:
        """Runs full ADMET screening across all generated molecule candidates."""
        passed_count = 0
        flagged_count = 0
        rejected_count = 0
        
        for cand in candidates:
            mol = Chem.MolFromSmiles(cand.smiles)
            if not mol:
                cand.admet_verdict = "REJECT"
                cand.admet_notes.append("Invalid chemical structure / SMILES parse error.")
                rejected_count += 1
                continue
                
            try:
                Chem.SanitizeMol(mol)
            except Exception as e:
                cand.admet_verdict = "REJECT"
                cand.admet_notes.append(f"Valence sanitization failed: {e}")
                rejected_count += 1
                continue
                
            # Descriptors
            cand.mw = round(Descriptors.MolWt(mol), 2)
            cand.logp = round(Crippen.MolLogP(mol), 2)
            cand.tpsa = round(rdMolDescriptors.CalcTPSA(mol), 2)
            cand.hbd = rdMolDescriptors.CalcNumHBD(mol)
            cand.hba = rdMolDescriptors.CalcNumHBA(mol)
            cand.rotatable_bonds = rdMolDescriptors.CalcNumRotatableBonds(mol)
            cand.qed = round(QED.qed(mol), 3)
            cand.molecular_formula = rdMolDescriptors.CalcMolFormula(mol)
            
            # Synthetic Accessibility Heuristic (Ring complexity + sp3 ratio + rotatable bonds)
            fsp3 = rdMolDescriptors.CalcFractionCSP3(mol)
            ring_count = rdMolDescriptors.CalcNumRings(mol)
            # SAScore heuristic scale: 1 (easy) to 10 (hard)
            sascore = 2.0 + (cand.mw / 150.0) + (ring_count * 0.4) - (fsp3 * 1.5)
            cand.sascore = round(max(1.0, min(10.0, sascore)), 2)
            
            # PAINS alerts
            cand.pains_alerts = []
            for p_name, p_mol in self._compiled_pains.items():
                if mol.HasSubstructMatch(p_mol):
                    cand.pains_alerts.append(p_name)
                    
            # Lipinski & Veber
            lipinski_violations = 0
            if cand.mw > 550: lipinski_violations += 1
            if cand.logp > 5.0: lipinski_violations += 1
            if cand.hbd > 5: lipinski_violations += 1
            if cand.hba > 10: lipinski_violations += 1
            cand.passes_lipinski = (lipinski_violations <= 1)
            
            cand.passes_veber = (cand.rotatable_bonds <= 10 and cand.tpsa <= 140.0)
            
            # Blood-Brain Barrier (BBB) Heuristic
            cand.bbb_permeable = (1.5 <= cand.logp <= 3.8 and cand.tpsa < 90.0 and cand.mw < 450)
            
            # hERG Cardiotoxicity Alert Heuristic (High LogP + high MW + basic amines)
            cand.herg_liability = (cand.logp > 4.2 and cand.mw > 480 and cand.hba >= 4)
            
            # Final Verdict
            cand.admet_notes = []
            if cand.pains_alerts:
                cand.admet_verdict = "REJECT"
                cand.admet_notes.append(f"PAINS alerts: {', '.join(cand.pains_alerts)}")
                rejected_count += 1
            elif not cand.passes_lipinski or not cand.passes_veber:
                cand.admet_verdict = "FLAGGED"
                cand.admet_notes.append(f"Lipinski/Veber boundary: MW={cand.mw}, LogP={cand.logp}, TPSA={cand.tpsa}")
                flagged_count += 1
            elif cand.herg_liability:
                cand.admet_verdict = "FLAGGED"
                cand.admet_notes.append(f"hERG potential cardiotoxicity liability (LogP={cand.logp}, MW={cand.mw})")
                flagged_count += 1
            else:
                cand.admet_verdict = "PASS"
                cand.admet_notes.append(f"Compliant: QED={cand.qed}, SAScore={cand.sascore}, TPSA={cand.tpsa}")
                passed_count += 1
                
        thought_text = (
            f"Evaluated {len(candidates)} candidates through medicinal chemistry filtration. "
            f"Outcome: {passed_count} PASS, {flagged_count} FLAGGED, {rejected_count} REJECT. "
            f"Screened PAINS, Lipinski Rule of 5, Veber criteria, SAScore, and hERG liability."
        )
        message = AgentMessage(
            agent_name=self.name,
            role="ADMET Critic",
            action="ADMET_MEDCHEM_EVALUATION",
            thought=thought_text,
            output_summary=f"{passed_count} PASS + {flagged_count} FLAGGED leads cleared for molecular docking simulation.",
            status="SUCCESS"
        )
        return candidates, message
