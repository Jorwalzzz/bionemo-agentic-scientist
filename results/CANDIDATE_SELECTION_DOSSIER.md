# Drug Candidate Selection Dossier: SARS-CoV-2 Mpro
**Target:** SARS-CoV-2 Mpro (ORF1ab) | **UniProt:** P0DTD1 | **PDB:** 7BQY  
**Date of Selection:** 2026-09-29 05:59:29 UTC  
**Principal Investigator:** Agentic BioNeMo Autonomous Discovery System  

---

## 1. Executive Summary & Clinical Rationale
Targeting oncogenic **SARS-CoV-2 Mpro** represents a transformative therapeutic avenue in clinical oncology. 
Viral main protease homodimer essential for processing viral polyproteins.

Using an autonomous closed-loop agentic workflow powered by **NVIDIA NIM MolMIM**, **RDKit ADMET screening**, and **NVIDIA NIM DiffDock**, we screened 2 bioisosteric derivatives of reference scaffold **Nirmatrelvir**.

### Key Discovery Highlights:
- **Nominated Lead:** `NIM-LEAD-01-01`
- **Predicted Binding Free Energy ($\Delta G$):** **-11.16 kcal/mol**
- **Drug-likeness (QED):** **0.504** (Complies with Lipinski Rule of 5)
- **Synthetic Accessibility Score:** **5.36 / 10**
- **Target Pocket Residue Contacts:** His41, Cys145, Glu166, Met49

---

## 2. Top Lead Candidates Ranked by Multi-Objective Pareto Frontier

| Lead ID | SMILES | $\Delta G$ (kcal/mol) | QED | MW (g/mol) | LogP | SAScore | Pareto? | ADMET Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **NIM-LEAD-01-01** | `CC1(C2C1C(N(C2)C(=O)C(C(C)(C...` | **-11.16** | 0.504 | 499.5 | 1.10 | 5.36 | ★ YES | `PASS` |
| **NIM-LEAD-01-02** | `CC1(C2C1C(N(C2)C(=O)C(C(C)(C...` | **-11.14** | 0.495 | 481.5 | 0.80 | 5.24 | ★ YES | `PASS` |

---

## 3. ADMET & Liability Assessment
- **Blood-Brain Barrier (BBB) Permeability:** 0 of top 2 leads meet CNS permeability heuristics.
- **Cardiotoxicity (hERG Alert):** 0 flagged liabilities.
- **PAINS Motifs:** 0 reactive or assay-interfering sub-structures in final leads.

---

## 4. Recommended Experimental Next Steps (In Vitro & In Vivo)
1. **Chemical Synthesis**: Solubilization and solid-phase synthesis targeting the core scaffold of `NIM-LEAD-01-01`.
2. **Biophysical Validation**: Surface Plasmon Resonance (SPR) and Microscale Thermophoresis (MST) to determine $K_D$ dissociation constant against recombinant SARS-CoV-2 Mpro.
3. **Cellular Target Engagement**: NanoBRET cellular kinase binding assay in mutant cell line.

---

## 🧬 Pipeline Architecture & Acknowledgements
- **Architected and Engineered by**: [Jorwalzzz](https://github.com/Jorwalzzz)
- **Generative Molecular Modeling & Docking**: Accelerated via NVIDIA BioNeMo™ & NIM™ microservices (MolMIM, DiffDock, ESM-2).
- **Cheminformatics & Structural Foundations**: Powered by RDKit, RCSB Protein Data Bank, and 3Dmol.js.
