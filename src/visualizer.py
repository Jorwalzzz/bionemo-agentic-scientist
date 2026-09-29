"""
Agentic BioNeMo - Publication Visualizer
Generates 300 DPI publication-grade figures: Pareto Frontier, Radar Profiles, and 2D Chemical Grids.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List
from rdkit import Chem
from rdkit.Chem import Draw
from src.models import MoleculeCandidate, TargetProfile

# Set elegant dark/clean publication aesthetic
sns.set_theme(style="whitegrid", font="sans-serif")
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.titlesize": 15,
    "savefig.dpi": 300,
    "savefig.bbox": "tight"
})

def plot_pareto_frontier(
    candidates: List[MoleculeCandidate],
    target: TargetProfile,
    output_path: str = "results/pareto_frontier.png"
):
    """Renders 300 DPI multi-objective Pareto scatter plot."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    docked = [c for c in candidates if c.binding_affinity < 0]
    if not docked:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, f"No Valid Docked Leads for {target.name}", 
                ha="center", va="center", fontsize=14, color="#64748b", fontweight="bold")
        ax.set_axis_off()
        fig.savefig(output_path, dpi=300)
        plt.close(fig)
        return

    fig, ax = plt.subplots(figsize=(10, 7))
    x = [c.binding_affinity for c in docked]
    y = [c.qed for c in docked]
    
    # Palette based on ADMET verdict
    colors = []
    for c in docked:
        if c.is_pareto_optimal:
            colors.append("#10b981") # Emerald star
        elif c.admet_verdict == "PASS":
            colors.append("#3b82f6") # Blue
        elif c.admet_verdict == "FLAGGED":
            colors.append("#f59e0b") # Amber
        else:
            colors.append("#ef4444") # Red
            
    scatter = ax.scatter(
        x, y,
        c=colors,
        s=[max(50, 180 - c.sascore * 12) for c in docked],
        alpha=0.85,
        edgecolors="black",
        linewidth=1.2,
        zorder=3
    )
    
    # Highlight Pareto optimal leads with stars
    for c in docked:
        if c.is_pareto_optimal:
            ax.scatter(c.binding_affinity, c.qed, marker="*", s=320, color="#fbbf24", edgecolors="#b45309", linewidth=1.5, zorder=5)
            ax.annotate(
                f"{c.id}\n(ΔG={c.binding_affinity:.2f})",
                (c.binding_affinity, c.qed),
                textcoords="offset points",
                xytext=(10, 8),
                fontsize=9,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", fc="#fef3c7", ec="#f59e0b", lw=1)
            )

    ax.set_xlabel("Predicted Binding Free Energy $\\Delta G$ (kcal/mol, more negative = stronger)", fontweight="bold")
    ax.set_ylabel("Drug-Likeness Quantitative Estimate (QED, 0 to 1)", fontweight="bold")
    ax.set_title(f"Agentic BioNeMo: Multi-Objective Lead Frontier for {target.name} ({target.pdb_id})\nNVIDIA NIM MolMIM Latent Exploration + DiffDock Molecular Docking", pad=15)
    
    # Safely add Superior Candidate Zone shading
    zone_min = min(x) - 0.5
    zone_max = min(max(x), -7.0)
    if zone_min < zone_max:
        ax.axvspan(zone_min, zone_max, ymin=0.45, ymax=1.0, color="#d1fae5", alpha=0.35, label="Optimal Clinical Lead Zone")
    
    # Custom Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='*', color='w', markerfacecolor='#fbbf24', markeredgecolor='#b45309', markersize=14, label='Pareto Frontier Lead'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#3b82f6', markeredgecolor='black', markersize=10, label='ADMET Compliant (PASS)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#f59e0b', markeredgecolor='black', markersize=10, label='Borderline/Flagged'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#ef4444', markeredgecolor='black', markersize=10, label='Rejected (PAINS/Valence)')
    ]
    ax.legend(handles=legend_elements, loc="lower left", frameon=True, facecolor="#f8fafc", edgecolor="#cbd5e1")
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)

def plot_chemical_leads_grid(
    top_leads: List[MoleculeCandidate],
    output_path: str = "results/top_leads_chemical_grid.png"
):
    """Renders 2D chemical structure grid of nominated leads."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    mols = []
    legends = []
    for lead in top_leads[:6]:
        m = Chem.MolFromSmiles(lead.smiles)
        if m:
            mols.append(m)
            legends.append(f"{lead.id}\nΔG: {lead.binding_affinity:.2f} kcal/mol\nQED: {lead.qed:.3f} | SAScore: {lead.sascore:.1f}")
            
    if mols:
        img = Draw.MolsToGridImage(
            mols,
            molsPerRow=3,
            subImgSize=(350, 300),
            legends=legends,
            useSVG=False
        )
        img.save(output_path)
    else:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "No Chemical Scaffolds Available for Grid View", 
                ha="center", va="center", fontsize=12, color="#64748b", fontweight="bold")
        ax.set_axis_off()
        fig.savefig(output_path, dpi=300)
        plt.close(fig)
