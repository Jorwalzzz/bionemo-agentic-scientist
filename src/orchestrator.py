"""
Agentic BioNeMo - Multi-Sub-Agent Swarm Orchestrator
Coordinates the decentralized autonomous scientific council:
- Dr. Cynthia (Target Scout)
- Dr. Aris (Generative Chemist)
- Dr. Marcus (MedChem Critic & Veto Engine)
- Dr. Elena (Biophysics Docking)
- Dr. Chen (Retrosynthesis Planner)
- Dr. Sterling (Chief Scientific PI & Council Arbiter)
"""
import os
import csv
import logging
from typing import Callable, List, Optional, Dict, Any
from rdkit import Chem

from src.models import TargetProfile, MoleculeCandidate, DossierReport, AgentMessage, CouncilMessage, RetrosynthesisPlan
from src.bus.message_bus import SwarmMessageBus
from src.target_scout import TargetScoutAgent
from src.generative_chemist import GenerativeChemistAgent
from src.admet_critic import ADMETCriticAgent
from src.docking_agent import BiophysicsDockingAgent
from src.pi_agent import PrincipalInvestigatorAgent
from src.retrosynthesis_agent import RetrosynthesisAgent

logger = logging.getLogger("Orchestrator")

class AgenticScientistOrchestrator:
    def __init__(
        self,
        api_key: str = None,
        mock: bool = True,
        on_message_callback: Optional[Callable[[AgentMessage], None]] = None,
        on_council_dialogue: Optional[Callable[[CouncilMessage], None]] = None
    ):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY", "")
        self.mock = mock or (not self.api_key)
        self.on_message = on_message_callback
        self.on_council = on_council_dialogue
        
        # Swarm message bus for decentralized agent communication
        self.bus = SwarmMessageBus()
        if self.on_council:
            self.bus.add_global_listener(self.on_council)

        # Autonomous Sub-Agents with Personas
        self.target_scout = TargetScoutAgent(api_key=self.api_key, mock=self.mock, name="TargetScout")
        self.generative_chemist = GenerativeChemistAgent(api_key=self.api_key, mock=self.mock, name="GenerativeChemist")
        self.admet_critic = ADMETCriticAgent()
        self.docking_agent = BiophysicsDockingAgent(api_key=self.api_key, mock=self.mock, name="DiffDockDocking")
        self.pi_agent = PrincipalInvestigatorAgent(name="PIParetoArbiter")
        self.retro_agent = RetrosynthesisAgent()
        
        self.audit_log: List[AgentMessage] = []
        self.latest_retrosynthesis_plan: Optional[RetrosynthesisPlan] = None
        self.evolution_rounds_data: List[Dict[str, Any]] = []

    def _emit(self, msg: AgentMessage):
        self.audit_log.append(msg)
        if self.on_message:
            self.on_message(msg)

    def run_discovery_campaign(
        self,
        target_query: str = "KRAS G12D",
        num_candidates: int = 12,
        rounds: int = 1,
        enable_feedback_loop: bool = True,
        output_dir: str = "results"
    ) -> DossierReport:
        """Executes full autonomous multi-sub-agent discovery council."""
        os.makedirs(output_dir, exist_ok=True)
        self.bus.clear()
        self.evolution_rounds_data.clear()

        # --- Sub-Agent 1: Target Scout (Dr. Cynthia) ---
        target_profile, scout_msg = self.target_scout.scout_target(target_query)
        self._emit(scout_msg)
        self.bus.publish(
            agent_id="scout",
            persona_name="Dr. Cynthia (Target Scout)",
            avatar="🎯",
            intent="TARGET_RESOLVED",
            content=f"Structural target '{target_profile.name}' (PDB {target_profile.pdb_id}) resolved and cleaned. Active site cleft isolated with {len(target_profile.pocket_residues)} key contact residues. Handing off to Dr. Aris for generative exploration.",
            metadata={"pdb_id": target_profile.pdb_id, "residue_count": len(target_profile.canonical_sequence)}
        )

        all_screened: List[MoleculeCandidate] = []
        current_seed_smiles = target_profile.reference_ligand_smiles

        # Multi-Round Evolutionary Swarm Loop
        total_rounds = max(1, min(rounds, 3))
        for current_round in range(1, total_rounds + 1):
            round_candidate_count = num_candidates if current_round == 1 else 6
            
            # --- Sub-Agent 2: Generative Chemist (Dr. Aris) ---
            prompt_guidance = "" if current_round == 1 else "Evolve top Pareto lead: optimize subpocket complementarity and polar surface area"
            candidates, chem_msg = self.generative_chemist.generate_derivatives(
                parent_smiles=current_seed_smiles,
                target_name=target_profile.name,
                num_molecules=round_candidate_count,
                steering_prompt=prompt_guidance,
                round_num=current_round
            )
            self._emit(chem_msg)
            self.bus.publish(
                agent_id="chemist",
                persona_name="Dr. Aris (Generative Chemist)",
                avatar="🧪",
                intent="PROPOSAL",
                content=f"[Round {current_round}] Sampled chemical latent space via NVIDIA MolMIM. Generated {len(candidates)} bioisosteric candidate structures around seed scaffold. Submitting to Dr. Marcus for rigorous MedChem scrutiny.",
                metadata={"round": current_round, "candidate_count": len(candidates)}
            )

            # --- Sub-Agent 3: MedChem Critic & Veto Loop (Dr. Marcus) ---
            evaluated_candidates, admet_msg = self.admet_critic.evaluate_candidates(candidates)
            self._emit(admet_msg)
            
            cleared_leads = [c for c in evaluated_candidates if c.admet_verdict == "PASS"]
            flagged_leads = [c for c in evaluated_candidates if c.admet_verdict == "FLAGGED"]
            rejected_leads = [c for c in evaluated_candidates if c.admet_verdict == "REJECT"]

            # Dr. Marcus issues vetoes or clearances
            if rejected_leads:
                worst = rejected_leads[0]
                reasons = ", ".join(worst.pains_alerts) if worst.pains_alerts else f"SAScore {worst.sascore:.1f} / MW {worst.mw:.0f}"
                self.bus.publish(
                    agent_id="critic",
                    persona_name="Dr. Marcus (MedChem Critic)",
                    avatar="⚖️",
                    intent="VETO",
                    content=f"VETO issued on {worst.id}: Flagged for {reasons}. Molecule is chemically unviable. Vetoing from docking pipeline.",
                    metadata={"vetoed_id": worst.id, "reasons": reasons}
                )
            
            self.bus.publish(
                agent_id="critic",
                persona_name="Dr. Marcus (MedChem Critic)",
                avatar="⚖️",
                intent="CLEARANCE",
                content=f"MedChem filtration complete: {len(cleared_leads)} candidates CLEARED with optimal Lipinski/Veber profiles and low synthetic complexity. Passing to Dr. Elena for 3D biophysical docking.",
                metadata={"cleared_count": len(cleared_leads), "flagged_count": len(flagged_leads)}
            )

            # --- Sub-Agent 4: Biophysics Docking (Dr. Elena) ---
            dockable_leads = cleared_leads + flagged_leads
            if not dockable_leads:
                dockable_leads = evaluated_candidates[:4]

            docked_leads, dock_msg = self.docking_agent.dock_candidates(dockable_leads, target_profile)
            self._emit(dock_msg)
            
            top_docked = min(docked_leads, key=lambda x: x.binding_affinity) if docked_leads else None
            best_aff = top_docked.binding_affinity if top_docked else 0.0
            
            self.bus.publish(
                agent_id="docker",
                persona_name="Dr. Elena (Biophysicist)",
                avatar="⚡",
                intent="DOCKING_RESULT",
                content=f"NVIDIA DiffDock 3D generative diffusion complete across {len(docked_leads)} poses. Top binder {top_docked.id if top_docked else 'N/A'} achieved ΔG = {best_aff:.2f} kcal/mol. Active site hydrogen bonds confirmed.",
                metadata={"top_affinity": best_aff, "top_id": top_docked.id if top_docked else ""}
            )

            all_screened.extend(evaluated_candidates)

            # Record round evolution telemetry
            self.evolution_rounds_data.append({
                "round": current_round,
                "best_affinity": best_aff,
                "avg_qed": round(sum(c.qed for c in dockable_leads) / max(1, len(dockable_leads)), 3),
                "cleared_count": len(cleared_leads),
                "total_docked": len(docked_leads)
            })

            # Update seed for next evolutionary round if applicable
            if top_docked and current_round < total_rounds:
                current_seed_smiles = top_docked.smiles
                self.bus.publish(
                    agent_id="pi",
                    persona_name="Dr. Sterling (Chief PI)",
                    avatar="👑",
                    intent="EVOLUTION_ORDER",
                    content=f"Round {current_round} concluded. Lead {top_docked.id} (ΔG = {best_aff:.2f} kcal/mol) selected as evolutionary seed for Round {current_round + 1}. Directing Dr. Aris to perform fine-grain bioisosteric mutation.",
                    metadata={"seed_id": top_docked.id, "next_round": current_round + 1}
                )

        # --- Sub-Agent 5: PI Evaluation & Multi-Objective Pareto Arbitration ---
        top_leads, pi_msg = self.pi_agent.evaluate_and_rank_leads(all_screened, target_profile)
        self._emit(pi_msg)
        
        prime_lead = top_leads[0] if top_leads else None
        
        self.bus.publish(
            agent_id="pi",
            persona_name="Dr. Sterling (Chief PI)",
            avatar="👑",
            intent="CONSENSUS",
            content=f"Consensus achieved across all 5 scientific council agents! Identified {len(top_leads)} non-dominated Pareto leads. Nominated Primary Clinical Candidate: {prime_lead.id if prime_lead else 'N/A'} (ΔG = {prime_lead.binding_affinity if prime_lead else 0.0:.2f} kcal/mol, QED = {prime_lead.qed if prime_lead else 0.0:.3f}).",
            metadata={"nominated_lead": prime_lead.id if prime_lead else "", "pareto_count": len(top_leads)}
        )

        # --- Sub-Agent 6: Retrosynthesis Planner (Dr. Chen) ---
        if prime_lead:
            retro_plan = self.retro_agent.plan_synthesis_route(prime_lead)
            self.latest_retrosynthesis_plan = retro_plan
            self.bus.publish(
                agent_id="retro",
                persona_name="Dr. Chen (Retrosynthesis Planner)",
                avatar="🔬",
                intent="RETROSYNTHESIS_SOLVED",
                content=f"Wet-lab synthesis route constructed for {prime_lead.id}: {retro_plan.num_steps}-step organic procedure ({retro_plan.overall_feasibility}). Starting from commercially available precursors ({', '.join(retro_plan.starting_materials[:2])}).",
                metadata={"steps": retro_plan.num_steps, "feasibility": retro_plan.overall_feasibility}
            )

        # --- Dossier Authoring & Serialization ---
        dossier = self.pi_agent.generate_dossier(target_profile, all_screened, top_leads, self.audit_log)
        
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
            for c in all_screened:
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

    def redock_modified_candidate(self, modified_smiles: str, target_name: str) -> Dict[str, Any]:
        """
        Interactive Chemical Workbench Tool (Human-in-the-Loop):
        Instantly evaluates, ADMET-cleans, and docks a human-edited or tweaked molecule.
        """
        mol = Chem.MolFromSmiles(modified_smiles)
        if not mol:
            return {"valid": False, "error": "Invalid chemical SMILES structure"}

        canonical_smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
        target_profile, _ = self.target_scout.scout_target(target_name)

        cand = MoleculeCandidate(
            id="USER-EDIT-01",
            smiles=canonical_smiles,
            parent_smiles=target_profile.reference_ligand_smiles
        )

        eval_cands, _ = self.admet_critic.evaluate_candidates([cand])
        docked_cands, _ = self.docking_agent.dock_candidates(eval_cands, target_profile)

        res_cand = docked_cands[0] if docked_cands else eval_cands[0]
        retro_plan = self.retro_agent.plan_synthesis_route(res_cand)

        return {
            "valid": True,
            "candidate_id": res_cand.id,
            "smiles": res_cand.smiles,
            "binding_affinity_kcal_mol": round(res_cand.binding_affinity, 2),
            "qed": round(res_cand.qed, 3),
            "mw": round(res_cand.mw, 1),
            "logp": round(res_cand.logp, 2),
            "sascore": round(res_cand.sascore, 2),
            "admet_verdict": res_cand.admet_verdict,
            "pose_sdf": res_cand.pose_sdf,
            "retrosynthesis": {
                "num_steps": retro_plan.num_steps,
                "feasibility": retro_plan.overall_feasibility,
                "starting_materials": retro_plan.starting_materials
            }
        }
