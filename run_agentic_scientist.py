"""
Agentic BioNeMo - Autonomous Multi-Agent AI Scientist
CLI Runner for Autonomous Target-to-Lead Drug Discovery Campaign.
"""
import os
import sys

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme

from src.models import AgentMessage
from src.orchestrator import AgenticScientistOrchestrator
from src.visualizer import plot_pareto_frontier, plot_chemical_leads_grid

custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "scout": "bold cyan",
    "chemist": "bold green",
    "critic": "bold yellow",
    "docking": "bold blue",
    "pi": "bold magenta"
})
console = Console(theme=custom_theme, force_terminal=True)

def display_agent_message(msg: AgentMessage):
    """Renders real-time agent thoughts and actions in rich terminal panels."""
    icons = {
        "TargetScout": ("🎯", "scout"),
        "GenerativeChemist": ("🧪", "chemist"),
        "ADMETCritic": ("🛡️", "critic"),
        "BiophysicsDocking": ("🔬", "docking"),
        "DiffDockDocking": ("🔬", "docking"),
        "PIParetoArbiter": ("👩‍🔬", "pi"),
        "RetrosynthesisAgent": ("⚗️", "chemist"),
        "PrincipalInvestigator": ("👩‍🔬", "pi")
    }
    icon, style = icons.get(msg.agent_name, (">", "cyan"))
    
    panel_title = f"{icon} [{style}]{msg.agent_name} ({msg.role})[/] | [white bold]{msg.action}[/]"
    content = f"[italic white]{msg.thought}[/italic white]\n\n[bold green]--> {msg.output_summary}[/]"
    console.print(Panel(content, title=panel_title, border_style=style, expand=False))

def main():
    parser = argparse.ArgumentParser(description="Agentic BioNeMo: Autonomous Multi-Agent AI Drug Discovery Scientist")
    parser.add_argument("--target", type=str, default="KRAS G12D", help="Clinical target query or 4-letter RCSB PDB code (e.g. KRAS G12D, EGFR T790M, 6LU7, 2ITZ)")
    parser.add_argument("--candidates", type=int, default=12, help="Number of chemical candidates to generate per round")
    parser.add_argument("--mock", action="store_true", default=True, help="Run in zero-credit simulation mock mode")
    parser.add_argument("--no-feedback", action="store_true", help="Disable PI autonomous feedback loop")
    parser.add_argument("--output", type=str, default="results", help="Output directory for artifacts")
    args = parser.parse_args()

    console.print("\n[bold green]================================================================================[/bold green]")
    console.print("[bold white] AGENTIC BIONEMO: AUTONOMOUS TARGET-TO-LEAD AI SCIENTIST[/bold white]")
    console.print("[dim cyan] Powered by NVIDIA NIM (MolMIM + DiffDock + ESM-2), RDKit, and Multi-Agent Reasoning[/dim cyan]")
    console.print("[bold green]================================================================================[/bold green]\n")

    orchestrator = AgenticScientistOrchestrator(
        mock=args.mock,
        on_message_callback=display_agent_message
    )

    console.print(f"[bold yellow]> Initiating Autonomous Discovery Campaign for Target:[/] [bold white underline]{args.target}[/]\n")
    
    dossier = orchestrator.run_discovery_campaign(
        target_query=args.target,
        num_candidates=args.candidates,
        enable_feedback_loop=not args.no_feedback,
        output_dir=args.output
    )

    # Render Table of Nominated Leads
    console.print("\n[bold green]TOP NOMINATED CLINICAL LEADS (PARETO FRONTIER RANKED)[/bold green]")
    table = Table(show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("Rank", justify="center", style="bold")
    table.add_column("Lead ID", style="bold cyan")
    table.add_column("Delta G (kcal/mol)", justify="right", style="bold green")
    table.add_column("QED", justify="right", style="cyan")
    table.add_column("MW", justify="right")
    table.add_column("LogP", justify="right")
    table.add_column("SAScore", justify="right")
    table.add_column("Pareto?", justify="center", style="bold yellow")
    table.add_column("ADMET Verdict", justify="center")

    for i, lead in enumerate(dossier.top_leads, 1):
        pareto_mark = "YES" if lead.is_pareto_optimal else "-"
        verdict_style = "[green]PASS[/]" if lead.admet_verdict == "PASS" else "[yellow]FLAGGED[/]"
        table.add_row(
            str(i),
            lead.id,
            f"{lead.binding_affinity:.2f}",
            f"{lead.qed:.3f}",
            f"{lead.mw:.1f}",
            f"{lead.logp:.2f}",
            f"{lead.sascore:.2f}",
            pareto_mark,
            verdict_style
        )
    console.print(table)

    # Render Publication Visualizations
    console.print("\n[bold cyan]Generating 300 DPI Publication Plots...[/bold cyan]")
    plot_pareto_frontier(dossier.top_leads, dossier.target, output_path=os.path.join(args.output, "pareto_frontier.png"))
    plot_chemical_leads_grid(dossier.top_leads, output_path=os.path.join(args.output, "top_leads_chemical_grid.png"))
    console.print(f"[bold green]Plots saved to {args.output}/[/bold green]")
    console.print(f"[bold green]Formal Dossier authored to {args.output}/CANDIDATE_SELECTION_DOSSIER.md[/bold green]")
    if orchestrator.latest_retrosynthesis_plan:
        rp = orchestrator.latest_retrosynthesis_plan
        console.print(f"\n[bold green]RETROSYNTHESIS ROUTE PLAN (Lead Candidate: {rp.candidate_id})[/bold green]")
        console.print(f"[cyan]Feasibility: {rp.overall_feasibility} | Synthesis Steps: {rp.num_steps}[/cyan]")
        for s in rp.steps:
            console.print(f"  Step {s.step_number}: [yellow]{s.reaction_type}[/] ({s.difficulty}) -> Yield ~{s.estimated_yield_pct}% | Reagents: {', '.join(s.reagents)}")
        console.print(f"  Starting Materials: [dim]{', '.join(rp.starting_materials)}[/dim]\n")
    console.print(f"[bold green]3D Docked Poses saved to {args.output}/top_leads_docked.sdf[/bold green]\n")

if __name__ == "__main__":
    main()
