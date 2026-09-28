"""
Agentic BioNeMo - Multi-Agent Orchestrator
Coordinates the closed-loop autonomous drug discovery cycle, managing agent communications,
state machine transitions, and experimental artifact serialization.
"""
import os
import csv
import logging
from typing import Callable, List, Optional
from rdkit import Chem

from src.models import TargetProfile, MoleculeCandidate, DossierReport, AgentMessage
from src.target_scout import TargetScoutAgent
from src.generative_chemist import GenerativeChemistAgent
from src.admet_critic import ADMETCriticAgent
from src.docking_agent import BiophysicsDockingAgent
from src.pi_agent import PrincipalInvestigatorAgent

logger = logging.getLogger("Orchestrator")

class AgenticScientistOrchestrator:
    def __init__(
        self,
        api_key: str = None,
        mock: bool = True,
        on_message_callback: Optional[Callable[[AgentMessage], None]] = None
    ):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        self.mock = mock or (not self.api_key)
        self.on_message = on_message_callback
        
        # Instantiate 5 autonomous agents
        self.target_scout = TargetScoutAgent()
        self.generative_chemist = GenerativeChemistAgent(api_key=self.api_key, mock=self.mock)
        self.admet_critic = ADMETCriticAgent()
        self.docking_agent = BiophysicsDockingAgent(api_key=self.api_key, mock=self.mock)
        self.pi_agent = PrincipalInvestigatorAgent()
        
        self.audit_log: List[AgentMessage] = []

    def _emit(self, msg: AgentMessage):
        self.audit_log.append(msg)
        if self.on_message:
            self.on_message(msg)

    def run_discovery_campaign(
        self,
        target_query: str = "KRAS G12D",
        num_candidates: int = 12,
        enable_feedback_loop: bool = True,
        output_dir: str = "results"
    ) -> DossierReport:
        """Executes full autonomous multi-agent discovery cycle."""
        os.makedirs(output_dir, exist_ok=True)
        
        # --- Stage 1: Target Scouting ---
        target_profile, scout_msg = self.target_scout.scout_target(target_query)
        self._emit(scout_msg)
        
        # --- Stage 2: Generative Chemistry Exploration (Round 1) ---
        candidates, chem_msg = self.generative_chemist.generate_derivatives(
            parent_smiles=target_profile.reference_ligand_smiles,
            target_name=target_profile.name,
            num_molecules=num_candidates,
            round_num=1
        )
        self._emit(chem_msg)
        
        # --- Stage 3: ADMET & MedChem Criticism ---
        evaluated_candidates, admet_msg = self.admet_critic.evaluate_candidates(candidates)
        self._emit(admet_msg)
        
        # --- Stage 4: Biophysics & DiffDock Docking ---
        docked_leads, dock_msg = self.docking_agent.dock_candidates(evaluated_candidates, target_profile)
        self._emit(dock_msg)
        
        # --- Stage 5: PI Evaluation & Pareto Ranking ---
        top_leads, pi_msg = self.pi_agent.evaluate_and_rank_leads(docked_leads, target_profile)
        self._emit(pi_msg)
        
        # --- Optional Stage 6: Autonomous Feedback Loop (Round 2) ---
        if enable_feedback_loop and top_leads:
            best = top_leads[0]
            # If top lead has mild synthetic or weight liabilities, trigger steering directive
            if best.mw > 500 or best.sascore > 4.5:
                feedback_msg = AgentMessage(
                    agent_name="PrincipalInvestigator",
                    role="Principal Investigator",
                    action="PI_STEERING_DIRECTIVE",
                    thought=(
                        f"Round 1 top lead {best.id} demonstrates strong affinity ({best.binding_affinity:.2f} kcal/mol) "
                        f"but has synthetic complexity (SAScore {best.sascore:.2f}) and MW ({best.mw:.1f} g/mol). "
                        f"Directing Generative Chemist to optimize polar surface and reduce steric hindrance."
                    ),
                    output_summary="Issued feedback directive: lower MW and optimize synthetic accessibility.",
                    status="SUCCESS"
                )
                self._emit(feedback_msg)
                
                # Round 2 Generative Chemistry with feedback
                r2_candidates, r2_chem_msg = self.generative_chemist.generate_derivatives(
                    parent_smiles=best.smiles,
                    target_name=target_profile.name,
                    num_molecules=6,
                    steering_prompt="Lower molecular weight, optimize QED and synthetic accessibility",
                    round_num=2
                )
                self._emit(r2_chem_msg)
                
                # Screen and Dock Round 2
                r2_eval, r2_admet_msg = self.admet_critic.evaluate_candidates(r2_candidates)
                self._emit(r2_admet_msg)
                
                r2_docked, r2_dock_msg = self.docking_agent.dock_candidates(r2_eval, target_profile)
                self._emit(r2_dock_msg)
                
                # Combine all candidates and re-rank
                all_candidates = candidates + r2_candidates
                top_leads, final_pi_msg = self.pi_agent.evaluate_and_rank_leads(all_candidates, target_profile)
                self._emit(final_pi_msg)
            else:
                all_candidates = candidates
        else:
            all_candidates = candidates

        # --- Stage 7: Dossier Authoring & Serialization ---
        dossier = self.pi_agent.generate_dossier(target_profile, all_candidates, top_leads, self.audit_log)
        
        # Save Dossier Markdown
        dossier_path = os.path.join(output_dir, "CANDIDATE_SELECTION_DOSSIER.md")
        with open(dossier_path, "w", encoding="utf-8") as f:
            f.write(dossier.executive_summary)
            
        # Save Summary CSV
        csv_path = os.path.join(output_dir, "screened_candidates_summary.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Candidate_ID", "SMILES", "Binding_Affinity_kcal_mol", "DiffDock_Confidence",
                "QED", "MW", "LogP", "TPSA", "HBD", "HBA", "RotBonds", "SAScore",
                "PAINS_Alerts", "ADMET_Verdict", "Is_Pareto_Optimal", "Round"
            ])
            for c in all_candidates:
                writer.writerow([
                    c.id, c.smiles, c.binding_affinity, c.diffdock_confidence,
                    c.qed, c.mw, c.logp, c.tpsa, c.hbd, c.hba, c.rotatable_bonds, c.sascore,
                    ";".join(c.pains_alerts), c.admet_verdict, c.is_pareto_optimal, c.generation_round
                ])
                
        # Save Multi-Molecule SDF for Top Leads
        sdf_path = os.path.join(output_dir, "top_leads_docked.sdf")
        writer = Chem.SDWriter(sdf_path)
        for lead in top_leads:
            mol = Chem.MolFromMolBlock(lead.pose_sdf) if lead.pose_sdf else Chem.MolFromSmiles(lead.smiles)
            if mol:
                mol.SetProp("_Name", lead.id)
                mol.SetProp("Binding_Affinity_kcal_mol", f"{lead.binding_affinity:.2f}")
                mol.SetProp("QED", f"{lead.qed:.3f}")
                mol.SetProp("MW", f"{lead.mw:.1f}")
                mol.SetProp("LogP", f"{lead.logp:.2f}")
                mol.SetProp("ADMET_Verdict", lead.admet_verdict)
                mol.SetProp("Is_Pareto_Optimal", str(lead.is_pareto_optimal))
                writer.write(mol)
        writer.close()
        
        return dossier
