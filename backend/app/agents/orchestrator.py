"""
Agent Orchestrator
CRITICAL: Coordinates all 24 agents through 4 phases
"""
from typing import Dict, Any, List, Optional
from app.db import SessionRepository, AgentLogRepository, FactorRepository
from app.db.repositories import ForecasterResponseRepository
from app.agents import (
    DiscoveryAgent,
    ValidatorAgent,
    RatingConsensusAgent,
    HistoricalResearchAgent,
    CurrentDataResearchAgent,
    SynthesisAgent
)
from app.core.logging_config import get_logger
import asyncio
import time
from datetime import datetime

logger = get_logger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the 4-phase agent workflow:
    Phase 1: Factor Discovery (10 agents, parallel)
    Phase 2: Validation (2 agents, sequential: Validator → RatingConsensus merged)
    Phase 3: Research (10 agents, parallel)
    Phase 4: Synthesis (1 agent)
    """

    def __init__(self, session_id: str, question_text: str, agent_counts: Optional[Dict[str, int]] = None, forecaster_class: str = "balanced"):
        logger.info("=" * 60)
        logger.info(f"[ORCHESTRATOR] Initializing AgentOrchestrator")
        logger.info(f"[ORCHESTRATOR] Session ID: {session_id}")
        logger.info(f"[ORCHESTRATOR] Question: {question_text[:100]}...")
        
        self.session_id = session_id
        self.question_text = question_text
        
        # Forecaster class configuration
        from app.agents.prompts import FORECASTER_CLASSES
        if forecaster_class not in FORECASTER_CLASSES:
            logger.warning(f"[ORCHESTRATOR] Unknown forecaster_class '{forecaster_class}', defaulting to 'balanced'")
            forecaster_class = "balanced"
        self.forecaster_class = forecaster_class
        class_info = FORECASTER_CLASSES[forecaster_class]
        logger.info(f"[ORCHESTRATOR] Forecaster class: {forecaster_class} - {class_info['name']}")
        logger.info(f"[ORCHESTRATOR] Description: {class_info['description']}")
        
        # Agent counts configuration
        # If agent_counts provided, use them; otherwise use forecaster class defaults
        if agent_counts:
            logger.info(f"[ORCHESTRATOR] Agent counts provided: {agent_counts}")
            self.phase_1_count = agent_counts.get("phase_1_discovery", class_info["default_agent_counts"]["phase_1_discovery"])
            self.phase_2_count = agent_counts.get("phase_2_validation", class_info["default_agent_counts"]["phase_2_validation"])
            # Phase 3: Support separate historical/current counts
            # Backward compatibility: if phase_3_research is provided but not historical/current, split 50/50
            if "phase_3_research" in agent_counts and "phase_3_historical" not in agent_counts and "phase_3_current" not in agent_counts:
                total_research = agent_counts["phase_3_research"]
                self.phase_3_historical_count = total_research // 2
                self.phase_3_current_count = total_research - self.phase_3_historical_count
                self.phase_3_count = total_research
                logger.info(f"[ORCHESTRATOR] Using backward-compatible phase_3_research split: {self.phase_3_historical_count} historical, {self.phase_3_current_count} current")
            else:
                # Use provided historical/current counts or defaults
                self.phase_3_historical_count = agent_counts.get("phase_3_historical", class_info["default_agent_counts"]["phase_3_historical"])
                self.phase_3_current_count = agent_counts.get("phase_3_current", class_info["default_agent_counts"]["phase_3_current"])
                self.phase_3_count = self.phase_3_historical_count + self.phase_3_current_count
            self.phase_4_count = agent_counts.get("phase_4_synthesis", class_info["default_agent_counts"]["phase_4_synthesis"])
        else:
            logger.info(f"[ORCHESTRATOR] Using forecaster class defaults for '{forecaster_class}'")
            defaults = class_info["default_agent_counts"]
            self.phase_1_count = defaults["phase_1_discovery"]
            self.phase_2_count = defaults["phase_2_validation"]
            self.phase_3_historical_count = defaults["phase_3_historical"]
            self.phase_3_current_count = defaults["phase_3_current"]
            self.phase_3_count = self.phase_3_historical_count + self.phase_3_current_count
            self.phase_4_count = defaults["phase_4_synthesis"]
        
        logger.info(f"[ORCHESTRATOR] Phase counts: P1={self.phase_1_count}, P2={self.phase_2_count}, P3={self.phase_3_count} ({self.phase_3_historical_count} historical + {self.phase_3_current_count} current), P4={self.phase_4_count}")
        
        # Initialize repositories
        logger.info("[ORCHESTRATOR] Initializing repositories: SessionRepository, AgentLogRepository, FactorRepository, ForecasterResponseRepository")
        self.session_repo = SessionRepository()
        self.log_repo = AgentLogRepository()
        self.factor_repo = FactorRepository()
        self.response_repo = ForecasterResponseRepository()
        logger.info("[ORCHESTRATOR] Initialization complete")
        
        # Create forecaster response record at initialization
        logger.info(f"[ORCHESTRATOR] Creating forecaster response record for class: {forecaster_class}")
        response_record = self.response_repo.create_response(
            session_id=self.session_id,
            forecaster_class=forecaster_class,
            status="running"
        )
        self.response_id = response_record.get("id")
        logger.info(f"[ORCHESTRATOR] Forecaster response ID: {self.response_id}")

        # Track tokens in memory - will calculate total at end instead of incrementing
        # This avoids race conditions and reduces DB operations
        self.pending_tokens = 0
        
        self.all_factors = []
        self.validated_factors = []
        self.top_factors = []
        self.research_results = []

    async def run(self):
        """Execute the complete 4-phase workflow"""
        workflow_start_time = time.time()
        logger.info("=" * 60)
        logger.info("[ORCHESTRATOR] Starting 4-phase workflow")
        logger.info(f"[ORCHESTRATOR] Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(workflow_start_time))}")
        logger.info("=" * 60)
        
        try:
            # Update session status
            logger.info("[ORCHESTRATOR] Phase 0: Updating session status to 'running'")
            await self.update_session_status("running", "factor_discovery")

            # Phase 1: Factor Discovery
            phase_1_start = time.time()
            logger.info("=" * 60)
            logger.info(f"[ORCHESTRATOR] Phase 1: Factor Discovery ({self.phase_1_count} agents)")
            logger.info(f"[ORCHESTRATOR] Phase 1 start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(phase_1_start))}")
            logger.info("=" * 60)
            await self.run_phase_1()
            phase_1_duration = time.time() - phase_1_start
            logger.info(f"[ORCHESTRATOR] Phase 1 completed in {phase_1_duration:.2f}s ({phase_1_duration:.1f}s)")

            # Phase 2: Validation
            phase_2_start = time.time()
            logger.info("=" * 60)
            logger.info(f"[ORCHESTRATOR] Phase 2: Validation ({self.phase_2_count} agents)")
            logger.info(f"[ORCHESTRATOR] Phase 2 start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(phase_2_start))}")
            logger.info("=" * 60)
            await self.update_session_status("running", "validation")
            await self.run_phase_2()
            phase_2_duration = time.time() - phase_2_start
            logger.info(f"[ORCHESTRATOR] Phase 2 completed in {phase_2_duration:.2f}s ({phase_2_duration:.1f}s)")

            # Phase 3: Research
            phase_3_start = time.time()
            logger.info("=" * 60)
            logger.info(f"[ORCHESTRATOR] Phase 3: Research ({self.phase_3_count} agents)")
            logger.info(f"[ORCHESTRATOR] Phase 3 start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(phase_3_start))}")
            logger.info("=" * 60)
            try:
                await self.update_session_status("running", "research")
                await self.run_phase_3()
                phase_3_duration = time.time() - phase_3_start
                logger.info(f"[ORCHESTRATOR] Phase 3 completed in {phase_3_duration:.2f}s ({phase_3_duration:.1f}s)")
            except Exception as e:
                phase_3_duration = time.time() - phase_3_start
                logger.error(f"[ORCHESTRATOR] Phase 3 FAILED after {phase_3_duration:.2f}s: {e}", exc_info=True)
                raise

            # Phase 4: Synthesis
            phase_4_start = time.time()
            logger.info("=" * 60)
            logger.info(f"[ORCHESTRATOR] Phase 4: Synthesis ({self.phase_4_count} agent)")
            logger.info(f"[ORCHESTRATOR] Phase 4 start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(phase_4_start))}")
            logger.info("=" * 60)
            try:
                await self.update_session_status("running", "synthesis")
                final_prediction = await self.run_phase_4()
                phase_4_duration = time.time() - phase_4_start
                logger.info(f"[ORCHESTRATOR] Phase 4 completed in {phase_4_duration:.2f}s ({phase_4_duration:.1f}s)")
            except Exception as e:
                phase_4_duration = time.time() - phase_4_start
                logger.error(f"[ORCHESTRATOR] Phase 4 FAILED after {phase_4_duration:.2f}s: {e}", exc_info=True)
                logger.error(f"[ORCHESTRATOR] Phase 4 error details: {type(e).__name__}: {str(e)}")
                import traceback
                logger.error(f"[ORCHESTRATOR] Phase 4 traceback:\n{traceback.format_exc()}")
                raise

            # Note: total_cost_tokens column doesn't exist in DB, skip token calculation
            # Token usage is tracked in agent_logs table instead
            
            # Calculate total workflow duration
            workflow_duration = time.time() - workflow_start_time
            
            # Add duration and phase timings to prediction result
            if final_prediction:
                final_prediction["total_duration_seconds"] = round(workflow_duration, 2)
                final_prediction["phase_durations"] = {
                    "phase_1_discovery": round(phase_1_duration, 2),
                    "phase_2_validation": round(phase_2_duration, 2),
                    "phase_3_research": round(phase_3_duration, 2),
                    "phase_4_synthesis": round(phase_4_duration, 2),
                }
                # Format human-readable duration
                minutes = int(workflow_duration // 60)
                seconds = int(workflow_duration % 60)
                if minutes > 0:
                    final_prediction["total_duration_formatted"] = f"{minutes}m {seconds}s"
                else:
                    final_prediction["total_duration_formatted"] = f"{seconds}s"

            # Mark session as completed
            logger.info("[ORCHESTRATOR] Marking session as completed")
            self.session_repo.mark_completed(
                session_id=self.session_id,
                prediction_probability=final_prediction.get("prediction_probability"),
                confidence=final_prediction.get("confidence"),
                total_duration_seconds=round(workflow_duration, 2)
            )
            
            # Update forecaster response with prediction results
            logger.info("[ORCHESTRATOR] Updating forecaster response with prediction results")
            self.response_repo.update_response(
                response_id=self.response_id,
                prediction_result=final_prediction,
                prediction_probability=final_prediction.get("prediction_probability"),
                confidence=final_prediction.get("confidence"),
                total_duration_seconds=round(workflow_duration, 2),
                total_duration_formatted=final_prediction.get("total_duration_formatted"),
                phase_durations=final_prediction.get("phase_durations"),
                status="completed"
            )
            
            logger.info("=" * 60)
            logger.info("[ORCHESTRATOR] Workflow completed successfully!")
            logger.info(f"[ORCHESTRATOR] Total workflow duration: {workflow_duration:.2f}s ({workflow_duration:.1f}s)")
            logger.info(f"[ORCHESTRATOR] Phase timings:")
            logger.info(f"[ORCHESTRATOR]   Phase 1 (Discovery): {phase_1_duration:.2f}s")
            logger.info(f"[ORCHESTRATOR]   Phase 2 (Validation): {phase_2_duration:.2f}s")
            logger.info(f"[ORCHESTRATOR]   Phase 3 (Research): {phase_3_duration:.2f}s")
            logger.info(f"[ORCHESTRATOR]   Phase 4 (Synthesis): {phase_4_duration:.2f}s")
            logger.info("=" * 60)

        except Exception as e:
            workflow_duration = time.time() - workflow_start_time
            logger.error(f"[ORCHESTRATOR] Workflow failed after {workflow_duration:.2f}s: {e}", exc_info=True)
            # Store duration even on failure
            error_data = {
                "total_duration_seconds": round(workflow_duration, 2),
                "error": str(e)
            }
            minutes = int(workflow_duration // 60)
            seconds = int(workflow_duration % 60)
            if minutes > 0:
                error_data["total_duration_formatted"] = f"{minutes}m {seconds}s"
            else:
                error_data["total_duration_formatted"] = f"{seconds}s"
            # Mark session as completed (with duration recorded even on failure)
            self.session_repo.mark_completed(
                session_id=self.session_id,
                total_duration_seconds=round(workflow_duration, 2)
            )
            
            # Update forecaster response with error
            if hasattr(self, 'response_id'):
                self.response_repo.update_response(
                    response_id=self.response_id,
                    status="failed",
                    error_message=str(e),
                    total_duration_seconds=round(workflow_duration, 2),
                    total_duration_formatted=error_data.get("total_duration_formatted")
                )
            raise

    async def run_phase_1(self):
        """Phase 1: Run discovery agents in parallel"""
        logger.info(f"[PHASE 1] Starting {self.phase_1_count} discovery agents")
        
        async def run_discovery_agent(agent_num: int):
            agent_name = f"discovery_{agent_num}"
            logger.info(f"[PHASE 1] Creating agent log for {agent_name}")
            log_id = self.create_agent_log(agent_name, "factor_discovery")
            
            try:
                logger.info(f"[PHASE 1] Initializing DiscoveryAgent({agent_num})")
                logger.info(f"[PHASE 1] Importing from app.agents.discovery")
                agent = DiscoveryAgent(agent_num, session_id=self.session_id)
                
                logger.info(f"[PHASE 1] Executing {agent_name}")
                logger.info(f"[PHASE 1] Calling agent.execute()")
                output = await agent.execute({
                    "question_text": self.question_text,
                    "question_type": "binary"  # TODO: Get from session
                })
                
                logger.info(f"[PHASE 1] {agent_name} completed, tokens used: {agent.tokens_used}")
                logger.info(f"[PHASE 1] Updating agent log for {agent_name}")
                self.update_agent_log(
                    log_id=log_id,
                    status="completed",
                    output_data=output,
                    tokens_used=agent.tokens_used
                )
                
                # Insert factors into database
                factors_found = output.get("factors", [])
                logger.info(f"[PHASE 1] {agent_name} found {len(factors_found)} factors")
                logger.info(f"[PHASE 1] Inserting factors into database via factor_repo.create_factor()")
                for factor in factors_found:
                    self.factor_repo.create_factor(
                        session_id=self.session_id,
                        name=factor.get("name", ""),
                        description=factor.get("description"),
                        category=factor.get("category")
                    )
                
                return output
            except Exception as e:
                logger.error(f"[PHASE 1] {agent_name} failed: {e}", exc_info=True)
                self.update_agent_log(
                    log_id=log_id,
                    status="failed",
                    error_message=str(e)
                )
                raise
        
        # Run discovery agents in parallel (configurable count)
        logger.info(f"[PHASE 1] Creating {self.phase_1_count} parallel tasks")
        tasks = [run_discovery_agent(i) for i in range(1, self.phase_1_count + 1)]
        logger.info(f"[PHASE 1] Executing all tasks with asyncio.gather()")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all factors
        logger.info(f"[PHASE 1] Collecting results from {len(results)} agents")
        self.all_factors = []
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                logger.warning(f"[PHASE 1] Agent {i} returned exception: {result}")
                continue
            factors = result.get("factors", [])
            self.all_factors.extend(factors)
            logger.info(f"[PHASE 1] Agent {i} contributed {len(factors)} factors")
        
        logger.info(f"[PHASE 1] Phase complete: {len(self.all_factors)} total factors discovered")

    async def run_phase_2(self):
        """Phase 2: Run 2 validation agents sequentially (Validator → RatingConsensus merged)"""
        # Agent 11: Validator
        log_id = self.create_agent_log("validator", "validation")
        try:
            validator = ValidatorAgent(session_id=self.session_id)
            output = await validator.execute({
                "question_text": self.question_text,
                "factors": self.all_factors
            })
            self.update_agent_log(log_id, "completed", output, validator.tokens_used)
            raw_validated = output.get("validated_factors", [])
            
            # Normalize validator output format
            # Validator might return factors in different formats:
            # 1. [{'name': '...', 'description': '...'}] - correct format
            # 2. [{'Factor Name': 'description'}] - name as key
            # 3. [{'Factor1': 'desc1', 'Factor2': 'desc2'}] - multiple factors in one dict
            normalized_factors = []
            for factor in raw_validated:
                if isinstance(factor, dict):
                    # Check if it's already in correct format
                    if 'name' in factor and 'description' in factor:
                        normalized_factors.append(factor)
                    else:
                        # Factor name(s) are keys - need to extract them
                        # Handle both single factor dict and multi-factor dict
                        for key, value in factor.items():
                            # Skip if key is a standard field name
                            if key.lower() in ['name', 'description', 'category']:
                                continue
                            # This is a factor name as key
                            normalized_factors.append({
                                "name": key,
                                "description": value if isinstance(value, str) else str(value),
                                "category": factor.get("category", "unknown")
                            })
            
            self.validated_factors = normalized_factors
            logger.info(f"[PHASE 2] Validator returned {len(raw_validated)} factors, normalized to {len(normalized_factors)}")
        except Exception as e:
            self.update_agent_log(log_id, "failed", error_message=str(e))
            raise
        
        # Agent 12+13 (merged): RatingConsensus - Scores all factors AND selects top 5
        log_id = self.create_agent_log("rating_consensus", "validation")
        try:
            rating_consensus = RatingConsensusAgent(session_id=self.session_id)
            output = await rating_consensus.execute({
                "question_text": self.question_text,
                "factors": self.validated_factors
            })
            self.update_agent_log(log_id, "completed", output, rating_consensus.tokens_used)
            
            # Extract rated factors and top factors from merged output
            rated_factors = output.get("rated_factors", [])
            top_factors_raw = output.get("top_factors", [])
            
            logger.info(f"[PHASE 2] RatingConsensus returned {len(rated_factors)} rated factors and {len(top_factors_raw)} top factors")
            
            # Update factors with importance scores
            for rated_factor in rated_factors:
                factors = self.factor_repo.find_all({
                    "session_id": self.session_id,
                    "name": rated_factor.get("name")
                })
                if factors:
                    self.factor_repo.update_factor(
                        factor_id=factors[0]["id"],
                        importance_score=rated_factor.get("importance_score")
                    )
            
            # Normalize top_factors format
            self.top_factors = []
            for factor in top_factors_raw[:5]:  # Ensure exactly 5
                if isinstance(factor, dict):
                    if 'name' in factor:
                        self.top_factors.append(factor)
                    else:
                        # Factor name might be a key
                        factor_name = list(factor.keys())[0] if factor else "Unknown"
                        self.top_factors.append({
                            "name": factor_name,
                            "description": factor.get(factor_name, factor.get("description", "")),
                            "importance_score": factor.get("importance_score", factor.get("importance", 0))
                        })
            
            logger.info(f"[PHASE 2] Selected {len(self.top_factors)} top factors for research")
            for i, factor in enumerate(self.top_factors, 1):
                logger.info(f"[PHASE 2]   {i}. {factor.get('name', 'Unknown')} (importance: {factor.get('importance_score', 'N/A')})")
        except Exception as e:
            logger.error(f"[PHASE 2] RatingConsensus agent failed: {e}", exc_info=True)
            self.update_agent_log(log_id, "failed", error_message=str(e))
            raise

    async def run_phase_3(self):
        """Phase 3: Run research agents in parallel (configurable count)"""
        logger.info(f"[PHASE 3] Starting research phase ({self.phase_3_count} agents)")
        
        # Get top 5 factors (always research all top factors, regardless of agent count)
        logger.info("[PHASE 3] Fetching top factors from database")
        all_factors = self.factor_repo.get_session_factors(
            self.session_id,
            order_by_importance=True
        )
        logger.info(f"[PHASE 3] Found {len(all_factors)} total factors")
        
        if not all_factors:
            error_msg = "No factors found for research phase"
            logger.error(f"[PHASE 3] {error_msg}")
            raise ValueError(error_msg)
        
        # Always research top 5 factors (or all if fewer than 5)
        # Agents will be distributed across these factors using modulo
        top_factors = all_factors[:5]
        logger.info(f"[PHASE 3] Researching top {len(top_factors)} factors")
        
        if not top_factors:
            error_msg = "No top factors available for research"
            logger.error(f"[PHASE 3] {error_msg}")
            raise ValueError(error_msg)
        
        async def run_historical_research(agent_idx: int, factor: dict):
            agent_name = f"historical_{agent_idx + 1}"
            log_id = self.create_agent_log(agent_name, "research")
            
            try:
                agent = HistoricalResearchAgent(agent_idx + 1, session_id=self.session_id)
                output = await agent.execute({
                    "question_text": self.question_text,
                    "factor": factor
                })
                self.update_agent_log(log_id, "completed", output, agent.tokens_used)
                return output
            except Exception as e:
                logger.error(f"[PHASE 3] Historical agent {agent_idx + 1} failed: {e}", exc_info=True)
                self.update_agent_log(log_id, "failed", error_message=str(e))
                raise
        
        async def run_current_research(agent_idx: int, factor: dict):
            agent_name = f"current_{agent_idx + 1}"
            log_id = self.create_agent_log(agent_name, "research")
            
            try:
                agent = CurrentDataResearchAgent(agent_idx + 1, session_id=self.session_id)
                output = await agent.execute({
                    "question_text": self.question_text,
                    "factor": factor
                })
                self.update_agent_log(log_id, "completed", output, agent.tokens_used)
                return output
            except Exception as e:
                logger.error(f"[PHASE 3] Current agent {agent_idx + 1} failed: {e}", exc_info=True)
                self.update_agent_log(log_id, "failed", error_message=str(e))
                raise
        
        # Always research all top factors (up to 5)
        # Agents will be distributed across factors using modulo
        factors_to_research = top_factors
        
        # Use configured historical/current counts
        num_historical = self.phase_3_historical_count
        num_current = self.phase_3_current_count
        
        # Run historical research agents (distribute across factors)
        historical_tasks = [
            run_historical_research(i, factors_to_research[i % len(factors_to_research)])
            for i in range(num_historical)
        ]
        
        # Run current research agents (distribute across factors)
        current_tasks = [
            run_current_research(i, factors_to_research[i % len(factors_to_research)])
            for i in range(num_current)
        ]
        
        logger.info(f"[PHASE 3] Running {len(historical_tasks)} historical and {len(current_tasks)} current research agents concurrently")
        logger.info(f"[PHASE 3] Researching {len(factors_to_research)} factors")
        
        # Run all research agents concurrently (both historical and current)
        all_tasks = historical_tasks + current_tasks
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Split results back into historical and current
        historical_results = all_results[:len(historical_tasks)]
        current_results = all_results[len(historical_tasks):]
        
        # Log any exceptions
        for i, result in enumerate(historical_results):
            if isinstance(result, Exception):
                logger.error(f"[PHASE 3] Historical agent {i+1} failed: {result}", exc_info=True)
        for i, result in enumerate(current_results):
            if isinstance(result, Exception):
                logger.error(f"[PHASE 3] Current agent {i+1} failed: {result}", exc_info=True)
        
        # Group research results by factor name
        # Each factor gets research from multiple agents (distributed via modulo)
        factor_research = {}
        for factor in factors_to_research:
            factor_name = factor.get("name", "Unknown")
            factor_research[factor_name] = {
                "historical": [],
                "current": [],
                "factor_id": factor["id"]
            }
        
        # Collect historical research by factor
        for i, result in enumerate(historical_results):
            if isinstance(result, Exception):
                continue
            factor_idx = i % len(factors_to_research)
            factor_name = factors_to_research[factor_idx].get("name", "Unknown")
            if factor_name in factor_research:
                factor_research[factor_name]["historical"].append(result)
        
        # Collect current research by factor
        for i, result in enumerate(current_results):
            if isinstance(result, Exception):
                continue
            factor_idx = i % len(factors_to_research)
            factor_name = factors_to_research[factor_idx].get("name", "Unknown")
            if factor_name in factor_research:
                factor_research[factor_name]["current"].append(result)
        
        # Combine research summaries for each factor
        logger.info(f"[PHASE 3] Combining research summaries for {len(factor_research)} factors")
        for factor_name, research_data in factor_research.items():
            try:
                # Combine all historical analyses
                historical_analyses = [
                    r.get("historical_analysis", "") 
                    for r in research_data["historical"] 
                    if r.get("historical_analysis")
                ]
                historical_analysis = "\n\n".join(historical_analyses) if historical_analyses else "No historical analysis available"
                
                # Combine all current findings
                current_findings_list = [
                    r.get("current_findings", "") 
                    for r in research_data["current"] 
                    if r.get("current_findings")
                ]
                current_findings = "\n\n".join(current_findings_list) if current_findings_list else "No current findings available"
                
                # Collect all sources
                all_sources = []
                for r in research_data["historical"] + research_data["current"]:
                    sources = r.get("sources", [])
                    if isinstance(sources, list):
                        all_sources.extend(sources)
                
                research_summary = f"""Historical Analysis:
{historical_analysis}

Current Findings:
{current_findings}

Sources: {', '.join(set(all_sources)) if all_sources else 'None'}"""
                
                logger.info(f"[PHASE 3] Updating factor '{factor_name}' with research summary")
                self.factor_repo.update_factor(
                    factor_id=research_data["factor_id"],
                    research_summary=research_summary
                )
            except Exception as e:
                logger.error(f"[PHASE 3] Failed to update research for factor '{factor_name}': {e}", exc_info=True)
                # Continue with other factors even if one fails
        
        logger.info(f"[PHASE 3] Phase 3 completed successfully")

    async def run_phase_4(self):
        """Phase 4: Run synthesis agent"""
        logger.info("[PHASE 4] Starting synthesis phase")
        log_id = self.create_agent_log("synthesizer", "synthesis")
        
        try:
            # Get all research data
            logger.info("[PHASE 4] Fetching factors from database")
            factors = self.factor_repo.get_session_factors(self.session_id)
            logger.info(f"[PHASE 4] Found {len(factors)} factors")
            
            if not factors:
                error_msg = "No factors found for synthesis"
                logger.error(f"[PHASE 4] {error_msg}")
                self.update_agent_log(log_id, "failed", error_message=error_msg)
                raise ValueError(error_msg)
            
            # Log factor details
            for i, factor in enumerate(factors[:5], 1):  # Log first 5
                logger.info(f"[PHASE 4] Factor {i}: {factor.get('name', 'Unknown')} (importance: {factor.get('importance_score', 'N/A')})")
            
            research_data = {
                "factors": [
                    {
                        "name": f.get("name", "Unknown"),
                        "importance_score": f.get("importance_score"),
                        "research_summary": f.get("research_summary", "")
                    }
                    for f in factors
                ]
            }
            
            logger.info(f"[PHASE 4] Creating SynthesisAgent with forecaster_class: {self.forecaster_class}")
            synthesizer = SynthesisAgent(session_id=self.session_id, forecaster_class=self.forecaster_class)
            
            logger.info("[PHASE 4] Executing synthesizer")
            output = await synthesizer.execute({
                "question_text": self.question_text,
                "question_type": "binary",  # TODO: Get from session
                "factors": factors,
                "research": research_data
            })
            
            logger.info(f"[PHASE 4] Synthesis completed, tokens used: {synthesizer.tokens_used}")
            self.update_agent_log(log_id, "completed", output, synthesizer.tokens_used)
            
            # Format prediction result
            prediction_result = {
                "prediction": output.get("prediction", ""),
                "prediction_probability": output.get("prediction_probability", output.get("confidence", 0.5)),  # Fallback to confidence for backward compatibility
                "confidence": output.get("confidence", 0.7),  # Default confidence if not provided
                "reasoning": output.get("reasoning", ""),
                "key_factors": output.get("key_factors", [])
            }
            
            logger.info(f"[PHASE 4] Prediction: {prediction_result.get('prediction', 'N/A')[:100]}...")
            logger.info(f"[PHASE 4] Prediction Probability: {prediction_result.get('prediction_probability', 'N/A')}")
            logger.info(f"[PHASE 4] Confidence (in probability estimate): {prediction_result.get('confidence', 'N/A')}")
            
            return prediction_result
        except Exception as e:
            logger.error(f"[PHASE 4] Synthesis failed: {e}", exc_info=True)
            self.update_agent_log(log_id, "failed", error_message=str(e))
            raise

    async def update_session_status(
        self,
        status: str,
        phase: str = None,
        error: str = None
    ):
        """
        Update session status and phase.
        NOTE: The sessions table only stores question_text, question_type, timestamps, 
        and prediction results. Status is inferred from completed_at being set.
        
        Args:
            status: Session status (running, completed, failed) - logged only
            phase: Optional phase name - logged only
            error: Optional error message - logged only
        """
        # Log status changes but don't store in DB (columns don't exist)
        logger.info(f"[SESSION] Status update: {status}, phase: {phase}")
        if error:
            logger.warning(f"[SESSION] Error: {error}")

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
        
        Note: total_cost_tokens column doesn't exist in the sessions table.
        Token usage is tracked per-agent in agent_logs table.
        """
        # Get all agent logs for this session
        all_logs = self.log_repo.get_session_logs(self.session_id)
        
        # Sum tokens from all completed agents
        total_tokens = sum(
            log.get("tokens_used", 0) 
            for log in all_logs 
            if log.get("status") == "completed"
        )
        
        # Log the total but don't update DB (column doesn't exist)
        logger.info(f"[ORCHESTRATOR] Total tokens used: {total_tokens}")
