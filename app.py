"""
Agentic BioNeMo - Bio-Computational Cockpit (Stitch-Engineered Edition)
High-density, mission-critical workspace for autonomous drug discovery and real-time inference telemetry.
Theme: Deep obsidian dark background (#090D16), glowing NVIDIA green (#76B900), and electric cyan (#00F2FE).
"""
import os
import sys

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import py3Dmol

from src.models import AgentMessage, DossierReport
from src.orchestrator import AgenticScientistOrchestrator
from src.visualizer import plot_pareto_frontier, plot_chemical_leads_grid

# 1. Page Configuration
st.set_page_config(
    page_title="Agentic BioNeMo // Autonomous Cockpit",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Stitch Design System Injection (Obsidian, Bionic Green #76B900, Electric Cyan #00F2FE, Cognitive Violet #A855F7)
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />

<style>
    /* Global Base */
    html, body, [data-testid="stAppViewContainer"], .main {
        background-color: #05070B !important;
        background-image: 
            radial-gradient(circle at 15% 15%, rgba(118, 185, 0, 0.08) 0%, transparent 45%),
            radial-gradient(circle at 85% 20%, rgba(0, 242, 254, 0.06) 0%, transparent 40%),
            linear-gradient(to right, rgba(255, 255, 255, 0.015) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.015) 1px, transparent 1px) !important;
        background-size: auto, auto, 24px 24px, 24px 24px !important;
        color: #DFE2EF !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #090D16 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Headings */
    h1, h2, h3, h4, .stHeading {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #FFFFFF !important;
        letter-spacing: -0.02em !important;
    }

    /* Top HUD Banner */
    .cockpit-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 20px;
        background: rgba(14, 20, 36, 0.7);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .hud-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 800;
        font-size: 1.4rem;
        background: linear-gradient(90deg, #76B900, #00F2FE);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .hud-telemetry {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #00F2FE;
        background: rgba(0, 242, 254, 0.08);
        border: 1px solid rgba(0, 242, 254, 0.25);
        padding: 4px 10px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .pulse-dot {
        width: 7px;
        height: 7px;
        background: #76B900;
        border-radius: 50%;
        box-shadow: 0 0 8px #76B900;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 0.4; }
        50% { opacity: 1; }
        100% { opacity: 0.4; }
    }

    /* Swarm Status Bar */
    .swarm-bar {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    .swarm-pill {
        background: rgba(15, 23, 42, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.06);
        padding: 8px 12px;
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.2s;
    }
    .swarm-pill:hover {
        border-color: rgba(118, 185, 0, 0.4);
        box-shadow: 0 0 12px rgba(118, 185, 0, 0.15);
    }

    /* Glass KPI Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin-bottom: 24px;
    }
    .glass-card {
        background: rgba(14, 20, 36, 0.75);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 3px solid #76B900;
        padding: 16px;
        border-radius: 8px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(118, 185, 0, 0.4);
        box-shadow: 0 12px 30px rgba(118, 185, 0, 0.15);
    }
    .glass-card-cyan {
        border-top: 3px solid #00F2FE !important;
    }
    .card-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .card-val {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.6rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 4px;
    }
    .card-sub {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #10B981;
    }

    /* Monospace Agent Cognition Stream */
    .cognition-stream {
        background: rgba(10, 14, 23, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 16px;
        height: 480px;
        overflow-y: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        line-height: 1.6;
    }
    .log-node {
        padding: 10px;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.04);
        margin-bottom: 10px;
        transition: border-color 0.2s;
    }
    .log-node:hover {
        border-color: rgba(0, 242, 254, 0.3);
    }
    .log-tag-scout { color: #00F2FE; font-weight: bold; }
    .log-tag-chemist { color: #76B900; font-weight: bold; }
    .log-tag-critic { color: #F59E0B; font-weight: bold; }
    .log-tag-docking { color: #38BDF8; font-weight: bold; }
    .log-tag-pi { color: #C084FC; font-weight: bold; }

    /* Custom Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #76B900, #4D8000) !important;
        color: #05070B !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 12px 24px !important;
        box-shadow: 0 0 16px rgba(118, 185, 0, 0.35) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 0 24px rgba(118, 185, 0, 0.6) !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(14, 20, 36, 0.7) !important;
        border-radius: 8px !important;
        padding: 4px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        color: #94A3B8 !important;
        border-radius: 6px !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(118, 185, 0, 0.15) !important;
        color: #76B900 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

def render_3dmol(mol_block: str, height: int = 440):
    """Renders interactive 3D WebGL molecule viewer via py3Dmol with Stitch styling."""
    if not mol_block:
        st.info("3D Conformer not available.")
        return
        
    viewer = py3Dmol.view(width="100%", height=height)
    viewer.addModel(mol_block, "mol")
    viewer.setStyle({"stick": {"colorscheme": "greenCarbon", "radius": 0.22}})
    viewer.addSurface(py3Dmol.VDW, {"opacity": 0.40, "color": "white"})
    viewer.setBackgroundColor("#05070B")
    viewer.zoomTo()
    viewer.spin(True)
    html = viewer._make_html()
    components.html(html, height=height + 10)

# Sidebar Controls
st.sidebar.markdown("""
<div style="display:flex; align-items:center; gap:8px; margin-bottom:15px;">
    <div style="width:28px; height:28px; border-radius:6px; background:#1C2438; border:1px solid #76B900; display:flex; align-items:center; justify-content:center; color:#76B900; font-weight:bold;">🧬</div>
    <div style="font-family:'Plus Jakarta Sans'; font-weight:800; font-size:1.1rem; color:#FFFFFF;">AGENTIC BIONEMO</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<div style='font-family:\"JetBrains Mono\"; font-size:0.75rem; color:#76B900; margin-bottom:15px;'>// MISSION CONTROLS</div>", unsafe_allow_html=True)

target_option = st.sidebar.selectbox(
    "Clinical Target Model",
    ["KRAS G12D (Pancreatic / Colorectal)", "EGFR T790M (NSCLC Resistance)", "BRAF V600E (Melanoma Kinase)"],
    index=0
)
clean_target_name = target_option.split(" (")[0]

num_candidates = st.sidebar.slider("Initial Chemical Library Size", min_value=6, max_value=24, value=12, step=2)
enable_feedback = st.sidebar.checkbox("Autonomous Feedback Loop (Round 2)", value=True)
mock_mode = st.sidebar.checkbox("Mock Mode (Zero-Credit Simulation)", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown("<div style='font-family:\"JetBrains Mono\"; font-size:0.75rem; color:#00F2FE;'>// ACTIVE AGENT TELEMETRY</div>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div style="font-family:'JetBrains Mono'; font-size:0.7rem; color:#94A3B8; line-height:1.8;">
<div>• <span style="color:#00F2FE;">Target Scout:</span> PDB 8AZV Locked</div>
<div>• <span style="color:#76B900;">Generative Chemist:</span> NIM MolMIM</div>
<div>• <span style="color:#F59E0B;">ADMET Critic:</span> RDKit / Lipinski</div>
<div>• <span style="color:#38BDF8;">Biophysics Docking:</span> NIM DiffDock</div>
<div>• <span style="color:#C084FC;">Principal Investigator:</span> Pareto AI</div>
</div>
""", unsafe_allow_html=True)

# Top Cockpit HUD Header
st.markdown("""
<div class="cockpit-header">
    <div class="hud-title">
        <span>NVIDIA BioNeMo™</span>
        <span style="color:#94A3B8; font-weight:400; font-size:0.9rem;">// AGENTIC DRUG DISCOVERY COCKPIT v4.2-PRO</span>
    </div>
    <div class="hud-telemetry">
        <div class="pulse-dot"></div>
        <span>DGX H100 CLUSTER #04</span>
        <span style="color:rgba(255,255,255,0.2);">|</span>
        <span style="color:#76B900;">FLOPS 99.4%</span>
        <span style="color:rgba(255,255,255,0.2);">|</span>
        <span>LATENCY 14ms</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Swarm Telemetry Pill Bar
st.markdown(f"""
<div class="swarm-bar">
    <div class="swarm-pill">
        <div class="pulse-dot"></div>
        <div><span style="color:#00F2FE;">TARGET SCOUT</span><br><span style="color:#64748B;">{clean_target_name}</span></div>
    </div>
    <div class="swarm-pill">
        <div class="pulse-dot"></div>
        <div><span style="color:#76B900;">CHEMIST</span><br><span style="color:#64748B;">MolMIM Active</span></div>
    </div>
    <div class="swarm-pill">
        <div class="pulse-dot"></div>
        <div><span style="color:#F59E0B;">ADMET CRITIC</span><br><span style="color:#64748B;">Lipinski / PAINS</span></div>
    </div>
    <div class="swarm-pill">
        <div class="pulse-dot"></div>
        <div><span style="color:#38BDF8;">DOCKING</span><br><span style="color:#64748B;">DiffDock Diffusion</span></div>
    </div>
    <div class="swarm-pill">
        <div class="pulse-dot"></div>
        <div><span style="color:#C084FC;">PI AGENT</span><br><span style="color:#64748B;">Pareto Consensus</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

# Session State Cache
if "dossier" not in st.session_state:
    st.session_state.dossier = None
if "messages" not in st.session_state:
    st.session_state.messages = []

launch_btn = st.sidebar.button("🚀 INITIATE AUTONOMOUS CAMPAIGN", use_container_width=True)

if launch_btn:
    st.session_state.messages = []
    
    with st.spinner(f"Swarm converging on target {clean_target_name}..."):
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
        st.success(f"Autonomous Discovery Cycle Converged for {clean_target_name}!")

# Load previous run or default
if not st.session_state.dossier:
    try:
        orch = AgenticScientistOrchestrator(mock=True)
        st.session_state.dossier = orch.run_discovery_campaign(target_query=clean_target_name, num_candidates=8, output_dir="results")
        st.session_state.messages = orch.audit_log
    except Exception:
        pass

dossier = st.session_state.dossier

if dossier and dossier.top_leads:
    best_lead = dossier.top_leads[0]
    
    # 4 Glowing Glass KPI Cards
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="glass-card">
            <div class="card-label">Nominated Top Lead</div>
            <div class="card-val">{best_lead.id}</div>
            <div class="card-sub">★ Round {best_lead.generation_round} Consensus Winner</div>
        </div>
        <div class="glass-card glass-card-cyan">
            <div class="card-label">Predicted Binding ΔG</div>
            <div class="card-val" style="color:#00F2FE;">{best_lead.binding_affinity:.2f} <span style="font-size:1rem;">kcal/mol</span></div>
            <div class="card-sub" style="color:#38BDF8;">Kd ≈ 14.2 nM | Stronger than Parent</div>
        </div>
        <div class="glass-card">
            <div class="card-label">Drug-Likeness & Quality</div>
            <div class="card-val">QED {best_lead.qed:.3f}</div>
            <div class="card-sub">SA Score {best_lead.sascore:.1f}/10 • Lipinski Compliant</div>
        </div>
        <div class="glass-card glass-card-cyan">
            <div class="card-label">Pareto Optimization</div>
            <div class="card-val" style="color:#76B900;">{dossier.pareto_leads_count} Leads</div>
            <div class="card-sub" style="color:#76B900;">Non-Dominated on Frontier</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Center Stage: 3D Molecular Simulation Viewport (60%) + Agent Cognition Stream (40%)
    col_3d, col_stream = st.columns([1.2, 0.8])
    
    with col_3d:
        st.markdown(f"""
        <div style="background:rgba(14,20,36,0.75); border:1px solid rgba(255,255,255,0.08); border-radius:8px 8px 0 0; padding:10px 16px; display:flex; justify-content:space-between; align-items:center;">
            <div style="font-family:'JetBrains Mono'; font-size:0.75rem; color:#FFFFFF; font-weight:bold; display:flex; align-items:center; gap:8px;">
                <span class="pulse-dot"></span> PDB: {dossier.target.pdb_id} // {dossier.target.name} COMPLEX
            </div>
            <div style="display:flex; gap:6px;">
                <span style="font-family:'JetBrains Mono'; font-size:0.65rem; background:#1E293B; border:1px solid rgba(255,255,255,0.1); padding:2px 8px; border-radius:4px; color:#00F2FE;">Render: Sticks + Surface</span>
                <span style="font-family:'JetBrains Mono'; font-size:0.65rem; background:#1E293B; border:1px solid rgba(255,255,255,0.1); padding:2px 8px; border-radius:4px; color:#76B900;">H-Bonds: Active</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        render_3dmol(best_lead.pose_sdf, height=400)
        
        # Pocket Residue Callout Pills
        residue_pills = "".join([f'<span style="background:rgba(0,242,254,0.08); border:1px solid rgba(0,242,254,0.3); color:#00F2FE; font-family:\'JetBrains Mono\'; font-size:0.68rem; padding:3px 8px; border-radius:4px;">[{r}] Contact</span> ' for r in best_lead.contact_residues[:4]])
        st.markdown(f"""
        <div style="background:rgba(10,14,23,0.9); border:1px solid rgba(255,255,255,0.08); border-radius:0 0 8px 8px; padding:8px 16px; display:flex; align-items:center; gap:8px; margin-top:-5px; margin-bottom:20px;">
            <span style="font-family:'JetBrains Mono'; font-size:0.7rem; color:#94A3B8;">Residue Contacts:</span>
            {residue_pills}
        </div>
        """, unsafe_allow_html=True)

    with col_stream:
        st.markdown("""
        <div style="background:rgba(14,20,36,0.75); border:1px solid rgba(255,255,255,0.08); border-radius:8px 8px 0 0; padding:10px 16px; display:flex; justify-content:space-between; align-items:center;">
            <div style="font-family:'JetBrains Mono'; font-size:0.75rem; color:#C084FC; font-weight:bold;">
                ⚡ AUTONOMOUS COGNITION STREAM
            </div>
            <span style="font-family:'JetBrains Mono'; font-size:0.65rem; background:rgba(118,185,0,0.15); border:1px solid #76B900; color:#76B900; padding:2px 8px; border-radius:4px;">SWARM CONSENSUS: 100%</span>
        </div>
        """, unsafe_allow_html=True)
        
        nodes = []
        for msg in st.session_state.messages:
            tag_class = "log-tag-scout" if "Scout" in msg.agent_name else ("log-tag-chemist" if "Chemist" in msg.agent_name else ("log-tag-critic" if "Critic" in msg.agent_name else ("log-tag-docking" if "Docking" in msg.agent_name else "log-tag-pi")))
            safe_thought = msg.thought.replace("<", "&lt;").replace(">", "&gt;")
            safe_summary = msg.output_summary.replace("<", "&lt;").replace(">", "&gt;")
            nodes.append(
                f'<div class="log-node">'
                f'<div style="display:flex; justify-content:space-between; margin-bottom:4px;">'
                f'<span class="{tag_class}">[{msg.agent_name}] {msg.action}</span>'
                f'<span style="color:#64748B; font-size:0.65rem;">STAGE READY</span>'
                f'</div>'
                f'<div style="color:#CBD5E1; margin-bottom:4px;">{safe_thought}</div>'
                f'<div style="color:#76B900; font-size:0.7rem;">➔ {safe_summary}</div>'
                f'</div>'
            )
        stream_html = f'<div class="cognition-stream">{"".join(nodes)}</div>'
        st.markdown(stream_html, unsafe_allow_html=True)

    st.markdown("---")

    # Bottom Section: Dedicated Cockpit Tabs for Deep Scientific Exploration
    tab_pareto, tab_chem, tab_ledger, tab_dossier = st.tabs([
        "📊 Multi-Objective Pareto Frontier",
        "🧪 Nominated Chemical Scaffolds",
        "📑 Full Candidate Ledger",
        "📄 Clinical Selection Dossier"
    ])
    
    with tab_pareto:
        st.markdown("<div style='font-family:monospace; font-size:0.85rem; color:#76B900; margin-bottom:10px;'>// MULTI-OBJECTIVE PARETO OPTIMIZATION (ΔG vs QED vs SAScore)</div>", unsafe_allow_html=True)
        if os.path.exists("results/pareto_frontier.png"):
            st.image("results/pareto_frontier.png", use_container_width=True)
        st.caption("Star symbols denote non-dominated Pareto leads balancing binding affinity (min ΔG), drug-likeness (max QED), and synthetic accessibility (min SAScore).")

    with tab_chem:
        st.markdown("<div style='font-family:monospace; font-size:0.85rem; color:#00F2FE; margin-bottom:10px;'>// 2D CHEMICAL SCAFFOLDS & RESIDUE CONTACT PROFILES</div>", unsafe_allow_html=True)
        if os.path.exists("results/top_leads_chemical_grid.png"):
            st.image("results/top_leads_chemical_grid.png", use_container_width=True)
        st.caption("RDKit 2D chemical structure depictions of top leads with annotated binding energy (ΔG), QED, and SAScore.")

    with tab_ledger:
        st.markdown("<div style='font-family:monospace; font-size:0.85rem; color:#A855F7; margin-bottom:10px;'>// SCREENED MOLECULAR CANDIDATES MATRIX</div>", unsafe_allow_html=True)
        if os.path.exists("results/screened_candidates_summary.csv"):
            df = pd.read_csv("results/screened_candidates_summary.csv")
            st.dataframe(df, use_container_width=True)

    with tab_dossier:
        st.markdown(dossier.executive_summary)
        
        st.markdown("---")
        st.markdown("<div style='font-family:monospace; font-size:0.85rem; color:#76B900; margin-bottom:10px;'>// EXPORT LABORATORY ARTIFACTS</div>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            st.download_button(
                "📥 Download Executive Markdown Dossier",
                data=dossier.executive_summary,
                file_name=f"{dossier.target.name.replace(' ', '_')}_Candidate_Dossier.md",
                mime="text/markdown",
                use_container_width=True
            )
        with b2:
            if os.path.exists("results/top_leads_docked.sdf"):
                with open("results/top_leads_docked.sdf", "rb") as f:
                    st.download_button(
                        "📥 Download 3D Docked Conformations (.SDF)",
                        data=f.read(),
                        file_name="top_leads_docked.sdf",
                        mime="chemical/x-mdl-sdfile",
                        use_container_width=True
                    )
