"""
Noise Agent - Custom agent with X AI Lookup MCP integration
Specialized agent that uses external information lookup capabilities
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.services.xai_lookup import XAILookupMCP
import json


class NoiseAgentOutput(BaseModel):
    """Output schema for Noise Agent"""
    analysis: str = Field(description="Main analysis or response")
    lookup_results: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Results from X AI lookup tool if used"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score in the analysis"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="List of sources consulted"
    )


NOISE_AGENT_PROMPT = """You are a Noise Agent specialized in analyzing information with access to external lookup capabilities.

Your capabilities include:
- X AI Lookup: Access to web search, knowledge bases, and real-time data
- Critical analysis of information from multiple sources
- Identifying signal vs noise in data
- Providing well-sourced, evidence-based responses

When you need current information, facts, or data that may not be in your training data, use the xai_lookup tool to retrieve it.

Your task is to:
1. Analyze the given question or topic
2. Use xai_lookup when you need external information
3. Synthesize findings into a coherent analysis
4. Provide confidence scores based on source quality and consistency
5. Cite all sources used

Be thorough, critical, and evidence-based in your analysis."""


class NoiseAgent(BaseAgent):
    """
    Noise Agent with X AI Lookup MCP integration
    
    This agent extends BaseAgent with the ability to use external
    information lookup tools via the Model Context Protocol (MCP).
    """

    def __init__(
        self,
        agent_name: str = "noise_agent",
        phase: str = "analysis",
        max_retries: int = 3,
        timeout_seconds: int = 300
    ):
        super().__init__(
            agent_name=agent_name,
            phase=phase,
            system_prompt=NOISE_AGENT_PROMPT,
            output_schema=NoiseAgentOutput,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        self.xai_lookup = XAILookupMCP()

    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """
        Build user message from input data
        
        Args:
            input_data: Dictionary containing 'question' or 'topic' key
            
        Returns:
            Formatted user message string
        """
        question = input_data.get("question") or input_data.get("topic", "")
        context = input_data.get("context", "")
        
        message = f"Question/Topic: {question}"
        if context:
            message += f"\n\nContext: {context}"
        
        return message

    async def execute(
        self,
        input_data: Dict[str, Any],
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute the noise agent with tool calling support
        
        Overrides base execute to handle function calling with X AI Lookup
        """
        self.status = "running"

        if progress_callback:
            await progress_callback(self.agent_name, "started")

        # Get tool definition
        tool_def = self.xai_lookup.get_tool_definition()

        for attempt in range(self.max_retries):
            try:
                # Build user message
                user_message = await self.build_user_message(input_data)

                # Call Grok API with tool support
                import asyncio
                response = await asyncio.wait_for(
                    self.grok_service.chat_completion(
                        system_prompt=self.system_prompt,
                        user_message=user_message,
                        output_schema=None,  # Don't use structured output when using tools
                        tools=[tool_def],
                        tool_choice="auto"
                    ),
                    timeout=self.timeout_seconds
                )

                # Track tokens
                self.tokens_used = response["total_tokens"]

                # Build message history
                messages = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ]

                # Process tool calls if present
                if "tool_calls" in response and response["tool_calls"]:
                    # Add assistant message with tool calls
                    assistant_msg = {"role": "assistant", "content": response.get("content")}
                    assistant_msg["tool_calls"] = response["tool_calls"]
                    messages.append(assistant_msg)

                    # Execute tool calls
                    tool_results = []
                    for tool_call in response["tool_calls"]:
                        func_name = tool_call["function"]["name"]
                        func_args = json.loads(tool_call["function"]["arguments"])

                        if func_name == "xai_lookup":
                            result = await self.xai_lookup.execute(**func_args)
                            tool_results.append({
                                "tool_call_id": tool_call["id"],
                                "role": "tool",
                                "name": func_name,
                                "content": json.dumps(result)
                            })

                    # Add tool results to messages
                    messages.extend(tool_results)

                    # Get final response with tool results (no tools in this call)
                    final_response = await asyncio.wait_for(
                        self.grok_service.chat_completion_with_messages(
                            messages=messages,
                            output_schema=self.output_schema,
                            tools=None
                        ),
                        timeout=self.timeout_seconds
                    )

                    # Parse final response
                    content = final_response.get("content", "{}")
                    try:
                        raw_output = json.loads(content)
                    except json.JSONDecodeError:
                        # If not JSON, create output from content
                        raw_output = {
                            "analysis": content,
                            "confidence": 0.7,
                            "sources": []
                        }
                    validated_output = self.output_schema(**raw_output)
                else:
                    # No tool calls, but we used tools so response might not be structured
                    # Try to parse JSON from content
                    content = response.get("content", "{}")
                    try:
                        raw_output = json.loads(content)
                    except json.JSONDecodeError:
                        # If not JSON, create output from content
                        raw_output = {
                            "analysis": content,
                            "confidence": 0.7,
                            "sources": []
                        }
                    validated_output = self.output_schema(**raw_output)

                self.output_data = validated_output.model_dump()
                self.status = "completed"

                if progress_callback:
                    await progress_callback(self.agent_name, "completed", self.output_data)

                return self.output_data

            except asyncio.TimeoutError:
                self.error_message = f"Timeout after {self.timeout_seconds}s"
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

            except Exception as e:
                self.error_message = str(e)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

        self.status = "failed"
        if progress_callback:
            await progress_callback(self.agent_name, "failed", {"error": self.error_message})

        raise Exception(f"Agent {self.agent_name} failed after {self.max_retries} attempts: {self.error_message}")

