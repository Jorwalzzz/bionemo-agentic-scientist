<div align="center">

# 🧬 Agentic BioNeMo
### Autonomous Multi-Agent AI Scientist for Target-to-Lead Drug Discovery

[![CI](https://github.com/Jorwalzzz/bionemo-agentic-scientist/actions/workflows/ci.yml/badge.svg)](https://github.com/Jorwalzzz/bionemo-agentic-scientist/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-BioNeMo%20%7C%20NIM-76B900.svg)](https://build.nvidia.com)
[![RDKit](https://img.shields.io/badge/RDKit-Cheminformatics-blueviolet.svg)](https://www.rdkit.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*An autonomous artificial intelligence discovery system orchestrating specialized AI agents to generate, filter, dock, and optimize clinical drug candidates against high-priority oncology resistance targets (KRAS G12D, EGFR T790M, BRAF V600E).*

[Key Features](#-key-features) • [System Architecture](#-system-architecture) • [Quick Start](#-quick-start) • [Interactive 3D Cockpit](#-interactive-3D-web-cockpit) • [Multi-Agent Personas](#-the-5-autonomous-agents)

---

</div>

## 🌟 Key Features

- **Autonomous Closed-Loop Lead Optimization**: From raw biological target query (`"KRAS G12D"`) to structural pocket resolution, de novo latent generation, ADMET filtering, and 3D molecular docking.
- **NVIDIA NIM Microservices Integration**:
  - **MolMIM NIM**: Generative latent space search with CMA-ES property steering.
  - **DiffDock NIM**: Generative diffusion for 3D molecular docking and binding pose sampling.
- **Multi-Objective Pareto Optimization**: Non-dominated Pareto frontier calculation balancing Binding Free Energy ($\Delta G$ in kcal/mol), Drug-likeness ($QED$), and Synthetic Accessibility ($SAScore$).
- **Autonomous Feedback Refinement**: Principal Investigator (PI) agent identifies chemical liabilities in Round 1 and issues directive feedback steering to the Generative Chemist for Round 2 optimization.
- **Interactive 3D Web Cockpit**: WebGL molecular viewer powered by `Streamlit` and `py3Dmol` with real-time multi-agent reasoning stream.
- **300 DPI Publication Plots**: Automated high-resolution Pareto scatter plots and 2D RDKit chemical grid generation.
- **Automated Dossier Generation**: Formatted executive *Candidate Selection Dossier* in Markdown with embedded 3D SDF conformations.

---

## 🏛️ System Architecture

```mermaid
graph TD
    User["User Clinical Query (e.g. KRAS G12D)"] --> PI["Principal Investigator (PI) Agent"]
    
    subgraph DiscoveryLoop ["Autonomous Multi-Agent Loop"]
        PI --> TS["1. Target Scout Agent"]
        TS -->|"Target Profile, PDB, Pocket Residues & Seed"| GC["2. Generative Chemist Agent"]
        GC -->|"Latent Space Exploration (NIM MolMIM)"| AC["3. ADMET & MedChem Critic"]
        
        AC -->|"Lipinski, QED, PAINS, SAScore, BBB"| DA["4. Biophysics & Docking Agent"]
        DA -->|"3D Poses & ΔG Affinity (NIM DiffDock)"| PI
        
        PI -.->|"Round 2 Steering Directive (Feedback Loop)"| GC
    end
    
    PI --> Dossier["Candidate Selection Dossier (Markdown)"]
    PI --> Plots["300 DPI Publication Plots & 3D SDFs"]
    PI --> Cockpit["Interactive Streamlit 3D Cockpit (app.py)"]
```

---

## 🤖 The 5 Autonomous Agents

| Agent | Persona | Responsibilities & Tools |
| :--- | :--- | :--- |
| **🧬 Target Scout** | *Structural Biologist* | Resolves target queries, fetches 3D crystal structures (`8AZV`, `2ITZ`, `4MNE`), cleans heteroatoms, validates canonical 20 IUPAC residues, and maps catalytic pockets. |
| **🧪 Generative Chemist** | *De Novo Chemist* | Executes CMA-ES latent exploration around seed scaffolds via **NVIDIA NIM MolMIM**, synthesizing diverse bioisosteric derivatives. |
| **🛡️ ADMET Critic** | *Medicinal Chemist* | RDKit valence sanitization, Lipinski Rule of 5, Veber criteria, QED drug-likeness, PAINS reactive alerts, SAScore, and hERG cardiotoxicity heuristics. |
| **📐 Biophysics Docking** | *Structural Modeler* | Conformer generation via ETKDGv3, 3D molecular docking via **NVIDIA NIM DiffDock**, calculating binding free energy ($\Delta G$ in kcal/mol) and mapping residue contacts. |
| **👑 Principal Investigator** | *Research Director* | Arbitrates multi-objective Pareto frontiers, evaluates liabilities, issues Round 2 feedback steering directives, and authors the Candidate Selection Dossier. |

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and set up the environment:
```bash
git clone https://github.com/Jorwalzzz/bionemo-agentic-scientist.git
cd bionemo-agentic-scientist
pip install -r requirements.txt
```

### 2. Autonomous CLI Discovery Campaign
Run the headless multi-agent system on your target:
```bash
# Target KRAS G12D oncogene
python run_agentic_scientist.py --target "KRAS G12D" --candidates 10

# Target EGFR T790M gatekeeper resistance
python run_agentic_scientist.py --target "EGFR T790M" --candidates 10

# Target BRAF V600E constitutive kinase
python run_agentic_scientist.py --target "BRAF V600E" --candidates 10
```

### 3. Run the Test Suite
```bash
pytest tests/ -v
```

---

## 🧊 Interactive 3D Web Cockpit

Launch the Streamlit interactive dashboard:
```bash
streamlit run app.py
```

The browser UI provides:
1. **Target Mission Control**: One-click target selection (`KRAS G12D`, `EGFR T790M`, `BRAF V600E`).
2. **Live Agent Thought Stream**: Real-time expanders detailing each agent's hypothesis, evaluation, and critique.
3. **Interactive 3D Pocket Viewer**: Embedded `py3Dmol` canvas to rotate, zoom, and inspect 3D docked poses with electrostatic surfaces.
4. **Interactive Pareto Chart & Data Grid**: Filterable lead table with one-click export for CSV and multi-molecule SDF.

---

## 📊 Scientific Validation Results

Targeting the oncogenic **KRAS G12D switch-II pocket** (PDB: `8AZV`):
- **Seed Scaffold**: MRTX1133 parent
- **Nominated Lead**: `NIM-LEAD-01-06`
- **Predicted Binding Energy ($\Delta G$):** **-9.05 kcal/mol**
- **Lipinski Compliance**: Passed with 0 PAINS structural alerts
- **Target Pocket Residue Contacts**: Asp12, Gly60, Gln61, Tyr96
- **Autonomous Feedback Optimization**: Round 2 steering reduced molecular complexity and optimized synthetic accessibility.

Artifacts generated automatically in `results/`:
- `results/pareto_frontier.png` (300 DPI publication scatter plot)
- `results/top_leads_chemical_grid.png` (2D chemical structure grid)
- `results/top_leads_docked.sdf` (3D conformer file ready for PyMOL)
- `results/CANDIDATE_SELECTION_DOSSIER.md` (Executive Selection Dossier)

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
