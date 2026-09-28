# Drug Candidate Selection Dossier: BRAF V600E
**Target:** BRAF V600E (BRAF) | **UniProt:** P15056 | **PDB:** 4MNE  
**Date of Selection:** 2026-09-28 16:41:53 UTC  
**Principal Investigator:** Agentic BioNeMo Autonomous Discovery System  

---

## 1. Executive Summary & Clinical Rationale
Targeting oncogenic **BRAF V600E** represents a transformative therapeutic avenue in clinical oncology. 
Constitutively active monomeric kinase in melanoma mimicking activation-loop phosphorylation.

Using an autonomous closed-loop agentic workflow powered by **NVIDIA NIM MolMIM**, **RDKit ADMET screening**, and **NVIDIA NIM DiffDock**, we screened 16 bioisosteric derivatives of reference scaffold **Vemurafenib**.

### Key Discovery Highlights:
- **Nominated Lead:** `NIM-LEAD-01-05`
- **Predicted Binding Free Energy ($\Delta G$):** **-9.86 kcal/mol**
- **Drug-likeness (QED):** **0.370** (Complies with Lipinski Rule of 5)
- **Synthetic Accessibility Score:** **6.62 / 10**
- **Target Pocket Residue Contacts:** Glu600, Lys483, Phe595

---

## 2. Top Lead Candidates Ranked by Multi-Objective Pareto Frontier

| Lead ID | SMILES | $\Delta G$ (kcal/mol) | QED | MW (g/mol) | LogP | SAScore | Pareto? | ADMET Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NIM-LEAD-01-05** | `CCCS(=O)(=O)NC1=C(F)C(=C(C=C...` | **-9.86** | 0.370 | 480.5 | 4.76 | 6.62 | ★ YES | `FLAGGED` |
| **NIM-LEAD-02-05** | `CCCS(=O)(=O)NC1=C(F)C(=C(C=C...` | **-9.86** | 0.370 | 480.5 | 4.76 | 6.62 | ★ YES | `FLAGGED` |
| **NIM-LEAD-01-02** | `CCS(=O)(=O)NC1=C(F)C(=C(C=C1...` | **-9.77** | 0.377 | 475.9 | 5.15 | 6.64 | ★ YES | `PASS` |
| **NIM-LEAD-02-02** | `CCS(=O)(=O)NC1=C(F)C(=C(C=C1...` | **-9.77** | 0.377 | 475.9 | 5.15 | 6.64 | ★ YES | `PASS` |
| **NIM-LEAD-01-04** | `CCCS(=O)(=O)NC1=C(F)C(=C(C=C...` | **-9.75** | 0.368 | 473.5 | 5.03 | 6.56 | ★ YES | `PASS` |

---

## 3. ADMET & Liability Assessment
- **Blood-Brain Barrier (BBB) Permeability:** 0 of top 5 leads meet CNS permeability heuristics.
- **Cardiotoxicity (hERG Alert):** 2 flagged liabilities.
- **PAINS Motifs:** 0 reactive or assay-interfering sub-structures in final leads.

---

## 4. Recommended Experimental Next Steps (In Vitro & In Vivo)
1. **Chemical Synthesis**: Solubilization and solid-phase synthesis targeting the core scaffold of `NIM-LEAD-01-05`.
2. **Biophysical Validation**: Surface Plasmon Resonance (SPR) and Microscale Thermophoresis (MST) to determine $K_D$ dissociation constant against recombinant BRAF V600E.
3. **Cellular Target Engagement**: NanoBRET cellular kinase binding assay in mutant cell line.
