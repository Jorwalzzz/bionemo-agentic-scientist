import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
"""
Agentic BioNeMo - Adversarial Stress Test Loop
Runs continuous closed-loop testing across diverse targets, library sizes,
and adversarial chemical edge cases to uncover and eliminate any latent bugs.
"""
import sys
import os
import random
import traceback

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.orchestrator import AgenticScientistOrchestrator
from src.visualizer import plot_pareto_frontier, plot_chemical_leads_grid
from src.models import MoleculeCandidate

ADVERSARIAL_SMILES = [
    "",                                     # Empty string
    "INVALID_SMILES_STRING_12345",          # Unparseable
    "C1=CC=CC=C1.O.Cl",                     # Disconnected mixture / salts
    "c1ccccc1",                             # Benzene (very low MW, no HBD)
    "C" * 150,                              # Unrealistic aliphatic chain
    "O=C1C=CC(=O)C=C1",                     # PAINS Quinone
    "O=C1NC(=S)SC1",                        # PAINS Rhodanine
    "c1c(O)c(O)ccc1",                      # Catechol
    "CC(=O)OC1=CC=CC=C1C(=O)O",             # Aspirin (small molecule)
    "CN1CCN(CC1)C2=NC=C(Cl)C3=C2C(C4=C(F)C=CC=C4F)=CC=C3" # Complex hetero-aromatic
]

TARGETS = ["KRAS G12D", "EGFR T790M", "BRAF V600E", "UNKNOWN TARGET XYZ", "HER2", "TP53"]

def run_stress_test(iterations: int = 15):
    print(f"=== Starting Stress Test Loop ({iterations} Iterations) ===")
    errors = []
    
    for i in range(1, iterations + 1):
        target = random.choice(TARGETS)
        num_candidates = random.choice([4, 6, 8, 12])
        enable_feedback = random.choice([True, False])
        print(f"[{i}/{iterations}] Testing Target: '{target}' | Candidates: {num_candidates} | Feedback: {enable_feedback}...")
        
        try:
            orchestrator = AgenticScientistOrchestrator(mock=True)
            dossier = orchestrator.run_discovery_campaign(
                target_query=target,
                num_candidates=num_candidates,
                enable_feedback_loop=enable_feedback,
                output_dir="results/stress_test"
            )
            
            # Verify outputs
            assert dossier is not None, "Dossier is None"
            assert len(dossier.top_leads) > 0, "No top leads nominated"
            assert dossier.screened_count > 0, "Zero candidates screened"
            
            # Verify visualization generation
            plot_pareto_frontier(dossier.top_leads, dossier.target, "results/stress_test/pareto_frontier.png")
            plot_chemical_leads_grid(dossier.top_leads, "results/stress_test/top_leads_chemical_grid.png")
            
            # Inject Adversarial Candidate Testing
            print(f"    Testing ADMET & Docking on {len(ADVERSARIAL_SMILES)} adversarial structures...")
            adv_cands = [MoleculeCandidate(id=f"ADV-{idx}", smiles=smi, parent_smiles="") for idx, smi in enumerate(ADVERSARIAL_SMILES)]
            eval_adv, _ = orchestrator.admet_critic.evaluate_candidates(adv_cands)
            docked_adv, _ = orchestrator.docking_agent.dock_candidates(eval_adv, dossier.target)
            ranked_adv, _ = orchestrator.pi_agent.evaluate_and_rank_leads(docked_adv, dossier.target)
            
            print(f"    --> Iteration {i} PASSED successfully!")
        except Exception as e:
            err_msg = f"Iteration {i} FAILED: {str(e)}\n{traceback.format_exc()}"
            print(f"    [!] {err_msg}")
            errors.append(err_msg)
            
    print(f"\n=== Stress Test Finished: {iterations - len(errors)}/{iterations} Passed ===")
    if errors:
        print(f"Found {len(errors)} issues:")
        for err in errors:
            print(err)
        sys.exit(1)
    else:
        print("ALL ITERATIONS PASSED WITH ZERO ERRORS!")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run_stress_test(n)
