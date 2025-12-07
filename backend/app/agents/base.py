"""
Base Agent Class
CRITICAL: All agents inherit from this class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
from pydantic import BaseModel
from app.services.grok import GrokService
import asyncio
import logging

logger = logging.getLogger(__name__)


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
        timeout_seconds: int = 300
    ):
        self.agent_name = agent_name
        self.phase = phase
        self.system_prompt = system_prompt
        self.output_schema = output_schema
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.grok_service = GrokService()

        self.tokens_used = 0
        self.status = "initialized"
        self.output_data: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None

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
        self.status = "running"

        if progress_callback:
            await progress_callback(self.agent_name, "started")

        for attempt in range(self.max_retries):
            try:
                # Build user message from input data
                user_message = await self.build_user_message(input_data)

                # Call Grok API with structured output
                response = await asyncio.wait_for(
                    self.grok_service.chat_completion(
                        system_prompt=self.system_prompt,
                        user_message=user_message,
                        output_schema=self.output_schema
                    ),
                    timeout=self.timeout_seconds
                )

                # Track tokens
                self.tokens_used = response["total_tokens"]

                # Validate output against schema
                import json
                raw_output = json.loads(response["content"])
                validated_output = self.output_schema(**raw_output)

                self.output_data = validated_output.model_dump()
                self.status = "completed"

                if progress_callback:
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
