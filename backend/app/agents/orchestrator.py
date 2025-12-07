"""
Agent Orchestrator
CRITICAL: Coordinates all 24 agents through 4 phases
"""
from typing import Dict, Any, List
from app.db import SessionRepository, AgentLogRepository, FactorRepository
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
        
        # Initialize repositories
        self.session_repo = SessionRepository()
        self.log_repo = AgentLogRepository()
        self.factor_repo = FactorRepository()

        # Track tokens in memory - will calculate total at end instead of incrementing
        # This avoids race conditions and reduces DB operations
        self.pending_tokens = 0
        
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

            # Calculate total tokens from all agent logs and update session once at the end
            # This is more efficient than incrementing per phase and avoids race conditions
            self.calculate_and_update_total_tokens()

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
        """
        Update session status and phase
        
        DB Operation: UPDATE sessions
        See: app/agents/db_mapping.py for detailed documentation
        """
        self.session_repo.update_status(
            session_id=self.session_id,
            status=status,
            phase=phase,
            prediction_result=prediction_result
        )
        
        # Note: Error handling would go here if needed
        # For now, errors are handled at the agent log level

    def create_agent_log(self, agent_name: str, phase: str) -> str:
        """
        Create a new agent log entry (when agent starts)
        
        DB Operation: INSERT into agent_logs
        See: app/agents/db_mapping.py for detailed documentation
        
        Returns:
            log_id: The ID of the created log entry
        """
        log = self.log_repo.create_log(
            session_id=self.session_id,
            agent_name=agent_name,
            phase=phase,
            status="running"
        )
        return log["id"]
    
    def update_agent_log(
        self,
        log_id: str,
        status: str,
        output_data: Dict[str, Any] = None,
        tokens_used: int = 0,
        error_message: str = None
    ):
        """
        Update an agent log entry (when agent completes/fails)
        
        DB Operation: UPDATE agent_logs
        See: app/agents/db_mapping.py for detailed documentation
        
        Args:
            log_id: The log entry ID (from create_agent_log)
            status: Final status (completed, failed)
            output_data: Agent output data (validated JSON)
            tokens_used: Token count for this agent run
            error_message: Error message if failed
        """
        self.log_repo.update_log(
            log_id=log_id,
            status=status,
            output_data=output_data,
            tokens_used=tokens_used,
            error_message=error_message
        )
        
        # Accumulate tokens in memory (will be calculated at end)
        # Individual agent tokens are already stored in agent_logs.tokens_used
        if tokens_used > 0:
            self.pending_tokens += tokens_used
    
    def calculate_and_update_total_tokens(self):
        """
        Calculate total tokens from all agent logs and update session once.
        
        This is more efficient than incrementing per phase:
        - Reduces DB operations (4 updates → 1 update)
        - Eliminates race conditions entirely
        - Can recalculate from agent_logs if needed
        
        Alternative: Could calculate on-demand from agent_logs, but storing
        in sessions makes queries faster.
        """
        # Get all agent logs for this session
        all_logs = self.log_repo.get_session_logs(self.session_id)
        
        # Sum tokens from all completed agents
        total_tokens = sum(
            log.get("tokens_used", 0) 
            for log in all_logs 
            if log.get("status") == "completed"
        )
        
        # Update session once with final total
        # Use base repository update method (inherited from BaseRepository)
        self.session_repo.update(
            self.session_id,
            {"total_cost_tokens": total_tokens}
        )
