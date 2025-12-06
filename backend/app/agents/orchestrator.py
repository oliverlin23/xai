"""
Agent Orchestrator
CRITICAL: Coordinates all 24 agents through 4 phases
"""
from typing import Dict, Any, List
from app.core.supabase import get_supabase_client
import asyncio
from datetime import datetime


class AgentOrchestrator:
    """
    Orchestrates the 4-phase agent workflow:
    Phase 1: Factor Discovery (10 agents, parallel)
    Phase 2: Validation (3 agents, sequential)
    Phase 3: Research (10 agents, parallel)
    Phase 4: Synthesis (1 agent)
    """

    def __init__(self, session_id: str, question_text: str):
        self.session_id = session_id
        self.question_text = question_text
        self.supabase = get_supabase_client()

        self.all_factors = []
        self.validated_factors = []
        self.top_factors = []
        self.research_results = []

    async def run(self):
        """Execute the complete 4-phase workflow"""
        try:
            # Update session status
            await self.update_session_status("running", "factor_discovery")

            # Phase 1: Factor Discovery
            await self.run_phase_1()

            # Phase 2: Validation
            await self.update_session_status("running", "validation")
            await self.run_phase_2()

            # Phase 3: Research
            await self.update_session_status("running", "research")
            await self.run_phase_3()

            # Phase 4: Synthesis
            await self.update_session_status("running", "synthesis")
            final_prediction = await self.run_phase_4()

            # Update session with final result
            await self.update_session_status("completed", "synthesis", final_prediction)

        except Exception as e:
            await self.update_session_status("failed", error=str(e))
            raise

    async def run_phase_1(self):
        """Phase 1: Run 10 discovery agents in parallel"""
        # TODO: Implement discovery agents
        # tasks = [self.run_discovery_agent(i) for i in range(10)]
        # results = await asyncio.gather(*tasks)
        # self.all_factors = [factor for result in results for factor in result["factors"]]
        pass

    async def run_phase_2(self):
        """Phase 2: Run 3 validation agents sequentially"""
        # TODO: Implement validation agents
        # Agent 11: Validator
        # Agent 12: Rater
        # Agent 13: Consensus Builder
        pass

    async def run_phase_3(self):
        """Phase 3: Run 10 research agents in parallel"""
        # TODO: Implement research agents
        # 5 historical + 5 current data agents
        pass

    async def run_phase_4(self):
        """Phase 4: Run synthesis agent"""
        # TODO: Implement synthesis agent
        pass

    async def update_session_status(
        self,
        status: str,
        phase: str = None,
        prediction_result: Dict[str, Any] = None,
        error: str = None
    ):
        """Update session in Supabase"""
        update_data = {"status": status}

        if phase:
            update_data["current_phase"] = phase
        if prediction_result:
            update_data["prediction_result"] = prediction_result
            update_data["completed_at"] = datetime.utcnow().isoformat()
        if error:
            update_data["error_message"] = error

        self.supabase.table("sessions").update(update_data).eq("id", self.session_id).execute()

    async def log_agent_execution(
        self,
        agent_name: str,
        phase: str,
        status: str,
        output_data: Dict[str, Any] = None,
        tokens_used: int = 0,
        error_message: str = None
    ):
        """Log agent execution to Supabase"""
        log_entry = {
            "session_id": self.session_id,
            "agent_name": agent_name,
            "phase": phase,
            "status": status,
            "output_data": output_data,
            "tokens_used": tokens_used,
            "error_message": error_message,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat() if status in ["completed", "failed"] else None
        }

        self.supabase.table("agent_logs").insert(log_entry).execute()
