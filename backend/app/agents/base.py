"""
Base Agent Class
CRITICAL: All agents inherit from this class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
from app.services.grok import GrokService, GROK_MODEL_REASONING
from app.core.logging_config import get_logger, get_agent_logger
import asyncio
import time

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Base class for all superforecasting agents

    Features:
    - Grok API integration
    - Structured output validation via Pydantic
    - Token usage tracking
    - Progress callbacks
    - Error handling with retries
    """

    def __init__(
        self,
        agent_name: str,
        phase: str,
        system_prompt: str,
        output_schema: type[BaseModel],
        max_retries: int = 3,
        timeout_seconds: int = 300,
        session_id: Optional[str] = None,
        grok_model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        logger.info(f"[BASE AGENT] Initializing {agent_name} (phase: {phase})")
        self.agent_name = agent_name
        self.phase = phase
        self.system_prompt = system_prompt
        self.output_schema = output_schema
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.session_id = session_id
        self.temperature = temperature
        
        # Create agent-specific logger if session_id provided
        if session_id:
            self.agent_logger = get_agent_logger(session_id, agent_name)
        else:
            self.agent_logger = logger
        
        self.grok_service = GrokService(model=grok_model)
        logger.info(f"[BASE AGENT] GrokService model: {self.grok_service.model}")
        self.agent_logger.info(f"[{agent_name}] GrokService initialized, model: {self.grok_service.model}")

        self.tokens_used = 0
        self.status = "initialized"
        self.output_data: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None
        self.execution_start_time: Optional[float] = None
        self.execution_end_time: Optional[float] = None
        self.execution_duration: Optional[float] = None
        logger.info(f"[BASE AGENT] {agent_name} initialized successfully")
        self.agent_logger.info(f"[{agent_name}] Agent initialized successfully")

    async def execute(
        self,
        input_data: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Execute the agent with retry logic

        Args:
            input_data: Input data for the agent
            progress_callback: Optional callback for progress updates

        Returns:
            Validated output data
        """
        logger.info(f"[{self.agent_name}] Starting execution")
        self.execution_start_time = time.time()
        self.agent_logger.info("=" * 60)
        self.agent_logger.info(f"[{self.agent_name}] EXECUTION STARTED")
        self.agent_logger.info(f"[{self.agent_name}] Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.execution_start_time))}")
        self.agent_logger.info(f"[{self.agent_name}] Status: initialized -> running")
        self.status = "running"

        if progress_callback:
            logger.info(f"[{self.agent_name}] Calling progress_callback('started')")
            self.agent_logger.info(f"[{self.agent_name}] Progress callback: started")
            await progress_callback(self.agent_name, "started")

        for attempt in range(self.max_retries):
            logger.info(f"[{self.agent_name}] Attempt {attempt + 1}/{self.max_retries}")
            self.agent_logger.info(f"[{self.agent_name}] Attempt {attempt + 1}/{self.max_retries}")
            try:
                # Build user message from input data
                logger.info(f"[{self.agent_name}] Calling build_user_message()")
                self.agent_logger.info(f"[{self.agent_name}] Building user message from input data")
                user_message = await self.build_user_message(input_data)
                logger.info(f"[{self.agent_name}] User message built ({len(user_message)} chars)")
                self.agent_logger.info(f"[{self.agent_name}] User message: {user_message[:200]}...")

                # Determine if web search should be enabled (Phase 1 and Phase 3)
                enable_web_search = self.phase in ["factor_discovery", "research"]
                
                # Call Grok API with structured output
                logger.info(f"[{self.agent_name}] Calling grok_service.chat_completion()")
                self.agent_logger.info(f"[{self.agent_name}] Calling Grok API")
                if enable_web_search:
                    logger.info(f"[{self.agent_name}] Web search enabled for phase: {self.phase}")
                    self.agent_logger.info(f"[{self.agent_name}] Web search enabled")
                self.agent_logger.info(f"[{self.agent_name}] System prompt length: {len(self.system_prompt)} chars")
                self.agent_logger.info(f"[{self.agent_name}] Output schema: {self.output_schema.__name__}")
                logger.info(f"[{self.agent_name}] System prompt length: {len(self.system_prompt)} chars")
                logger.info(f"[{self.agent_name}] Output schema: {self.output_schema.__name__}")
                response = await asyncio.wait_for(
                    self.grok_service.chat_completion(
                        system_prompt=self.system_prompt,
                        user_message=user_message,
                        output_schema=self.output_schema,
                        enable_web_search=enable_web_search,
                        temperature=self.temperature
                    ),
                    timeout=self.timeout_seconds
                )
                logger.info(f"[{self.agent_name}] Grok API call successful")
                self.agent_logger.info(f"[{self.agent_name}] Grok API call successful")

                # Log web search usage if available
                if enable_web_search:
                    num_sources = response.get("num_sources_used")
                    web_indicators = response.get("web_search_indicators")
                    if num_sources is not None:
                        logger.info(f"[{self.agent_name}] Web search used {num_sources} sources")
                        self.agent_logger.info(f"[{self.agent_name}] Web search used {num_sources} sources")
                    elif web_indicators:
                        logger.info(f"[{self.agent_name}] Web search indicators: URLs={web_indicators.get('has_urls')}, Sources={web_indicators.get('has_sources')}")
                        self.agent_logger.info(f"[{self.agent_name}] Web search indicators: URLs={web_indicators.get('has_urls')}, Sources={web_indicators.get('has_sources')}")

                # Track tokens
                self.tokens_used = response["total_tokens"]
                logger.info(f"[{self.agent_name}] Tokens used: {self.tokens_used}")
                self.agent_logger.info(f"[{self.agent_name}] Tokens used: {self.tokens_used}")

                # Validate output against schema
                logger.info(f"[{self.agent_name}] Validating output against {self.output_schema.__name__}")
                self.agent_logger.info(f"[{self.agent_name}] Validating output against {self.output_schema.__name__}")
                import json
                raw_output = json.loads(response["content"])
                validated_output = self.output_schema(**raw_output)
                logger.info(f"[{self.agent_name}] Output validated successfully")
                self.agent_logger.info(f"[{self.agent_name}] Output validated successfully")
                self.agent_logger.info(f"[{self.agent_name}] Output data: {str(validated_output.model_dump())[:500]}...")

                self.output_data = validated_output.model_dump()
                
                # Store web search metadata in output_data for frontend display
                if enable_web_search:
                    num_sources = response.get("num_sources_used")
                    web_indicators = response.get("web_search_indicators")
                    if num_sources is not None:
                        self.output_data["_web_search_metadata"] = {
                            "sources_used": num_sources,
                            "web_search_enabled": True
                        }
                    elif web_indicators:
                        self.output_data["_web_search_metadata"] = {
                            "web_search_enabled": True,
                            "has_urls": web_indicators.get("has_urls", False),
                            "has_sources": web_indicators.get("has_sources", False)
                        }
                    else:
                        self.output_data["_web_search_metadata"] = {
                            "web_search_enabled": True
                        }
                
                self.status = "completed"
                self.execution_end_time = time.time()
                self.execution_duration = self.execution_end_time - self.execution_start_time
                
                logger.info(f"[{self.agent_name}] Status: running -> completed")
                logger.info(f"[{self.agent_name}] Execution time: {self.execution_duration:.2f}s")
                self.agent_logger.info(f"[{self.agent_name}] Status: running -> completed")
                self.agent_logger.info(f"[{self.agent_name}] End time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.execution_end_time))}")
                self.agent_logger.info(f"[{self.agent_name}] Execution duration: {self.execution_duration:.2f} seconds ({self.execution_duration:.1f}s)")
                self.agent_logger.info(f"[{self.agent_name}] Tokens used: {self.tokens_used}")
                self.agent_logger.info(f"[{self.agent_name}] Tokens per second: {self.tokens_used / self.execution_duration:.2f}" if self.execution_duration > 0 else "[{self.agent_name}] Tokens per second: N/A")
                self.agent_logger.info(f"[{self.agent_name}] EXECUTION COMPLETED SUCCESSFULLY")
                self.agent_logger.info("=" * 60)

                if progress_callback:
                    logger.info(f"[{self.agent_name}] Calling progress_callback('completed')")
                    await progress_callback(self.agent_name, "completed", self.output_data)

                return self.output_data

            except asyncio.TimeoutError:
                self.error_message = f"Timeout after {self.timeout_seconds}s"
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue

            except Exception as e:
                self.error_message = str(e)
                
                # Rate limit errors are already handled by GrokService with retries
                # But if they still fail after all retries, we should log and continue
                if "rate limit" in str(e).lower() or "429" in str(e):
                    logger.warning(f"Agent {self.agent_name} hit rate limit: {e}")
                    # GrokService already retried, so if we get here, it's a persistent issue
                    if attempt < self.max_retries - 1:
                        # Additional backoff on top of GrokService's retries
                        await asyncio.sleep(5 * (2 ** attempt))  # Longer backoff
                        continue
                
                # For other errors, use standard exponential backoff
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue

        self.status = "failed"
        self.execution_end_time = time.time()
        if self.execution_start_time:
            self.execution_duration = self.execution_end_time - self.execution_start_time
            logger.error(f"[{self.agent_name}] Execution failed after {self.execution_duration:.2f}s")
            self.agent_logger.error(f"[{self.agent_name}] End time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.execution_end_time))}")
            self.agent_logger.error(f"[{self.agent_name}] Execution duration: {self.execution_duration:.2f} seconds ({self.execution_duration:.1f}s)")
            self.agent_logger.error(f"[{self.agent_name}] EXECUTION FAILED")
        else:
            logger.error(f"[{self.agent_name}] Execution failed before start")
            self.agent_logger.error(f"[{self.agent_name}] EXECUTION FAILED (before start)")
        self.agent_logger.error(f"[{self.agent_name}] Error: {self.error_message}")
        self.agent_logger.info("=" * 60)
        
        if progress_callback:
            await progress_callback(self.agent_name, "failed", {"error": self.error_message})

        raise Exception(f"Agent {self.agent_name} failed after {self.max_retries} attempts: {self.error_message}")

    @abstractmethod
    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """
        Build user message from input data
        Must be implemented by subclasses
        """
        pass
