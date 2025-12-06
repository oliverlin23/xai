"""
Grok API service wrapper
CRITICAL: Handles async streaming, token tracking, and structured outputs
"""
from openai import AsyncOpenAI
from typing import AsyncIterator, Dict, Any, Optional
from pydantic import BaseModel
from app.core.config import get_settings
import asyncio


class GrokService:
    """
    Grok API wrapper with streaming support and token tracking
    """

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.grok_api_key,
            base_url="https://api.x.ai/v1"
        )
        self.model = "grok-beta"

    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: Optional[type[BaseModel]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Send chat completion request to Grok API

        Args:
            system_prompt: System prompt for the agent
            user_message: User message/question
            output_schema: Pydantic model for structured output (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Returns:
            Dict with 'content', 'prompt_tokens', 'completion_tokens'
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add structured output if schema provided
        if output_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": output_schema.__name__,
                    "schema": output_schema.model_json_schema(),
                    "strict": True
                }
            }

        try:
            response = await self.client.chat.completions.create(**kwargs)

            return {
                "content": response.choices[0].message.content,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        except Exception as e:
            raise Exception(f"Grok API error: {str(e)}")

    async def chat_completion_stream(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ) -> AsyncIterator[str]:
        """
        Stream chat completion from Grok API

        Args:
            system_prompt: System prompt for the agent
            user_message: User message/question
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        Yields:
            Chunks of text from the streaming response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"Grok API streaming error: {str(e)}")
