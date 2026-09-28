# Drug Candidate Selection Dossier: EGFR T790M
**Target:** EGFR T790M (EGFR) | **UniProt:** P00533 | **PDB:** 2ITZ  
**Date of Selection:** 2026-09-28 07:45:30 UTC  
**Principal Investigator:** Agentic BioNeMo Autonomous Discovery System  

---

## 1. Executive Summary & Clinical Rationale
Targeting oncogenic **EGFR T790M** represents a transformative therapeutic avenue in clinical oncology. 
Acquired clinical gatekeeper resistance mutation in NSCLC kinase domain conferring steric clash.

Using an autonomous closed-loop agentic workflow powered by **NVIDIA NIM MolMIM**, **RDKit ADMET screening**, and **NVIDIA NIM DiffDock**, we screened 10 bioisosteric derivatives of reference scaffold **Gefitinib**.

### Key Discovery Highlights:
- **Nominated Lead:** `NIM-LEAD-02-06`
- **Predicted Binding Free Energy ($\Delta G$):** **-9.06 kcal/mol**
- **Drug-likeness (QED):** **0.641** (Complies with Lipinski Rule of 5)
- **Synthetic Accessibility Score:** **5.77 / 10**
- **Target Pocket Residue Contacts:** Met790, Lys745, Thr854

---

## 2. Top Lead Candidates Ranked by Multi-Objective Pareto Frontier

| Lead ID | SMILES | $\Delta G$ (kcal/mol) | QED | MW (g/mol) | LogP | SAScore | Pareto? | ADMET Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NIM-LEAD-02-06** | `CC1=C(OCC2CCNCC2)C=C3C(=C1)N...` | **-9.06** | 0.641 | 400.9 | 4.85 | 5.77 | ★ YES | `PASS` |
| **NIM-LEAD-01-01** | `COC1=C(OCC2CCNCC2)C=C3C(=C1)...` | **-9.12** | 0.614 | 416.9 | 4.55 | 5.88 | ★ YES | `PASS` |
| **NIM-LEAD-02-01** | `COC1=C(OCC2CCNCC2)C=C3C(=C1)...` | **-9.12** | 0.614 | 416.9 | 4.55 | 5.88 | ★ YES | `PASS` |
| **NIM-LEAD-02-05** | `COC1=C(OCC2CCNCC2)C=C3C(=C1)...` | **-9.11** | 0.606 | 406.5 | 3.88 | 5.85 | ★ YES | `PASS` |
| **NIM-LEAD-01-02** | `COC1=C(OCC2CCOCC2)C=C3C(=C1)...` | **-8.96** | 0.610 | 417.9 | 4.98 | 5.89 | No | `PASS` |

---

## 3. ADMET & Liability Assessment
- **Blood-Brain Barrier (BBB) Permeability:** 0 of top 5 leads meet CNS permeability heuristics.
- **Cardiotoxicity (hERG Alert):** 0 flagged liabilities.
- **PAINS Motifs:** 0 reactive or assay-interfering sub-structures in final leads.

---

## 4. Recommended Experimental Next Steps (In Vitro & In Vivo)
1. **Chemical Synthesis**: Solubilization and solid-phase synthesis targeting the core scaffold of `NIM-LEAD-02-06`.
2. **Biophysical Validation**: Surface Plasmon Resonance (SPR) and Microscale Thermophoresis (MST) to determine $K_D$ dissociation constant against recombinant EGFR T790M.
3. **Cellular Target Engagement**: NanoBRET cellular kinase binding assay in mutant cell line.
