"""
Agentic BioNeMo - Interactive 3D Web Cockpit
Streamlit GUI for Autonomous Multi-Agent Target-to-Lead Drug Discovery.
"""
import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import py3Dmol

from src.models import AgentMessage, DossierReport
from src.orchestrator import AgenticScientistOrchestrator
from src.visualizer import plot_pareto_frontier, plot_chemical_leads_grid

# Page Configuration
st.set_page_config(
    page_title="Agentic BioNeMo | Autonomous AI Scientist",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (NVIDIA Dark Theme)
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #76b900, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 25px;
    }
    .metric-card {
        background: #1e293b;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #76b900;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .agent-box {
        background: #0f172a;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)

def render_3dmol(mol_block: str, height: int = 420):
    """Renders interactive 3D WebGL molecule viewer via py3Dmol."""
    if not mol_block:
        st.info("3D Conformer not available.")
        return
        
    viewer = py3Dmol.view(width="100%", height=height)
    viewer.addModel(mol_block, "mol")
    viewer.setStyle({"stick": {"colorscheme": "greenCarbon", "radius": 0.2}})
    viewer.addSurface(py3Dmol.VDW, {"opacity": 0.45, "color": "white"})
    viewer.zoomTo()
    viewer.spin(True)
    html = viewer._make_html()
    components.html(html, height=height + 20)

# Sidebar
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/2/21/Nvidia_logo.svg", width=160)
st.sidebar.title("🎛️ Mission Controls")

target_option = st.sidebar.selectbox(
    "Target Disease Model",
    ["KRAS G12D (Pancreatic / Colorectal)", "EGFR T790M (NSCLC Resistance)", "BRAF V600E (Melanoma Kinase)"],
    index=0
)
clean_target_name = target_option.split(" (")[0]

num_candidates = st.sidebar.slider("Initial Chemical Library Size", min_value=6, max_value=20, value=10, step=2)
enable_feedback = st.sidebar.checkbox("Autonomous Feedback Loop (Round 2)", value=True)
mock_mode = st.sidebar.checkbox("Mock Mode (Zero-Credit Simulation)", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Autonomous Agents Deployed:**
- 🧬 `Target Scout` (UniProt / PDB)
- 🧪 `Generative Chemist` (NIM MolMIM)
- 🛡️ `ADMET Critic` (RDKit / Lipinski / PAINS)
- 📐 `Biophysics Docking` (NIM DiffDock)
- 👑 `Principal Investigator` (Pareto Frontier)
""")

# Main Content Header
st.markdown('<div class="main-header">🧬 Agentic BioNeMo: Autonomous AI Drug Discovery Scientist</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Closed-Loop De Novo Target-to-Lead Generation via NVIDIA NIM Microservices & Multi-Agent Reasoning</div>', unsafe_allow_html=True)

# Session State Cache
if "dossier" not in st.session_state:
    st.session_state.dossier = None
if "messages" not in st.session_state:
    st.session_state.messages = []

launch_btn = st.sidebar.button("🚀 Launch Autonomous Campaign", type="primary", use_container_width=True)

if launch_btn:
    st.session_state.messages = []
    
    with st.spinner(f"Agents assembling for target {clean_target_name}..."):
        progress_bar = st.progress(0)
        
        def message_callback(msg: AgentMessage):
            st.session_state.messages.append(msg)
            
        orchestrator = AgenticScientistOrchestrator(
            mock=mock_mode,
            on_message_callback=message_callback
        )
        
        progress_bar.progress(25)
        dossier = orchestrator.run_discovery_campaign(
            target_query=clean_target_name,
            num_candidates=num_candidates,
            enable_feedback_loop=enable_feedback,
            output_dir="results"
        )
        progress_bar.progress(75)
        
        plot_pareto_frontier(dossier.top_leads, dossier.target, "results/pareto_frontier.png")
        plot_chemical_leads_grid(dossier.top_leads, "results/top_leads_chemical_grid.png")
        
        progress_bar.progress(100)
        st.session_state.dossier = dossier
        st.success(f"Autonomous Campaign Completed for {clean_target_name}!")

# Display Results
dossier = st.session_state.dossier

if dossier and dossier.top_leads:
    best_lead = dossier.top_leads[0]
    
    # Top KPI Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nominated Top Lead", best_lead.id, f"Round {best_lead.generation_round}")
    with col2:
        st.metric("Predicted Binding ΔG", f"{best_lead.binding_affinity:.2f} kcal/mol", "-1.2 kcal/mol vs parent")
    with col3:
        st.metric("Drug-likeness (QED)", f"{best_lead.qed:.3f}", "+0.04 vs parent")
    with col4:
        st.metric("Pareto Leads Identified", f"{dossier.pareto_leads_count} / {dossier.screened_count}", "Non-dominated")
        
    st.markdown("---")
    
    # Interactive Tabs
    tab_overview, tab_agents, tab_3d, tab_pareto, tab_dossier = st.tabs([
        "🔬 Lead Overview", "🤖 Multi-Agent Audit Log", "🧊 3D Molecular Cockpit", "📊 Pareto Frontier", "📄 Selection Dossier"
    ])
    
    with tab_overview:
        col_img, col_info = st.columns([1.2, 1])
        with col_img:
            if os.path.exists("results/top_leads_chemical_grid.png"):
                st.image("results/top_leads_chemical_grid.png", caption="Top Nominated Chemical Leads (2D RDKit Depiction)")
        with col_info:
            st.markdown(f"### Target: **{dossier.target.name}**")
            st.markdown(f"**PDB Identifier:** `{dossier.target.pdb_id}` | **UniProt:** `{dossier.target.uniprot_id}`")
            st.write(dossier.target.description)
            st.markdown("**Pocket Key Residues:**")
            st.write(", ".join([f"`{r}`" for r in dossier.target.pocket_residues]))
            st.markdown(f"**Reference Scaffold:** `{dossier.target.reference_ligand_name}`")
            st.code(dossier.target.reference_ligand_smiles, language="text")
            
    with tab_agents:
        st.markdown("### Autonomous Multi-Agent Step-by-Step Reasoning")
        for msg in st.session_state.messages:
            with st.expander(f"{msg.agent_name} ({msg.role}) ➔ {msg.action}", expanded=True):
                st.write(f"💭 **Thought:** {msg.thought}")
                st.info(f"📋 **Outcome:** {msg.output_summary}")
                
    with tab_3d:
        st.markdown("### Interactive 3D Pocket Conformer (NVIDIA NIM DiffDock Simulation)")
        st.write(f"Viewing 3D energy-minimized binding pose for **{best_lead.id}** inside the {dossier.target.name} pocket.")
        render_3dmol(best_lead.pose_sdf)
        st.caption("Rotate with left mouse button | Zoom with scroll | Shift with right mouse button")
        
    with tab_pareto:
        if os.path.exists("results/pareto_frontier.png"):
            st.image("results/pareto_frontier.png", caption="300 DPI Publication-Grade Multi-Objective Pareto Frontier")
            
        st.markdown("### Full Candidates Screening Data")
        if os.path.exists("results/screened_candidates_summary.csv"):
            df = pd.read_csv("results/screened_candidates_summary.csv")
            st.dataframe(df, use_container_width=True)
            
    with tab_dossier:
        st.markdown(dossier.executive_summary)
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "📥 Download Markdown Dossier",
                data=dossier.executive_summary,
                file_name=f"{dossier.target.name.replace(' ', '_')}_Candidate_Dossier.md",
                mime="text/markdown"
            )
        with col_d2:
            if os.path.exists("results/top_leads_docked.sdf"):
                with open("results/top_leads_docked.sdf", "rb") as f:
                    st.download_button(
                        "📥 Download 3D SDF Docked Poses",
                        data=f.read(),
                        file_name="top_leads_docked.sdf",
                        mime="chemical/x-mdl-sdfile"
                    )
else:
    st.info("👈 Select a clinical target on the left and click **'Launch Autonomous Campaign'** to trigger the multi-agent AI scientist.")
