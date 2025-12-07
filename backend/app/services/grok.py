"""
Grok API service wrapper
CRITICAL: Handles async streaming, token tracking, structured outputs, and rate limiting
"""
from openai import AsyncOpenAI
from openai import RateLimitError, APIError, APIConnectionError, APITimeoutError
from typing import AsyncIterator, Dict, Any, Optional, List
from pydantic import BaseModel
from app.core.config import get_settings
from app.core.logging_config import get_logger
import asyncio
import random
from datetime import datetime, timedelta

logger = get_logger(__name__)


class GrokService:
    """
    Grok API wrapper with streaming support, token tracking, and rate limit handling
    
    Features:
    - Automatic rate limit detection and retry with exponential backoff
    - Request throttling to prevent hitting rate limits
    - Rate limit header parsing (if available)
    - Configurable retry behavior
    """

    def __init__(self):
        logger.info("[GROK SERVICE] Initializing GrokService")
        logger.info("[GROK SERVICE] Loading settings from app.core.config")
        settings = get_settings()
        logger.info("[GROK SERVICE] Creating AsyncOpenAI client (base_url: https://api.x.ai/v1)")
        self.client = AsyncOpenAI(
            api_key=settings.grok_api_key,
            base_url="https://api.x.ai/v1"
        )
        self.model = "grok-4-1-fast-reasoning"  # Grok 4.1 Fast Reasoning - optimized for agentic workflows
        logger.info(f"[GROK SERVICE] Model set to: {self.model}")
        
        # Rate limiting configuration (from settings or defaults)
        self.max_requests_per_minute = getattr(
            settings, 'grok_max_requests_per_minute', 60
        )
        self.max_concurrent_requests = getattr(
            settings, 'grok_max_concurrent_requests', 10
        )
        self.rate_limit_retry_attempts = getattr(
            settings, 'grok_rate_limit_retry_attempts', 5
        )
        self.base_retry_delay = 1.0  # Base delay in seconds for exponential backoff
        
        # Rate limiting state
        self.request_times = []  # Track request timestamps for rate limiting
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Rate limit tracking
        self.rate_limit_reset_at: Optional[datetime] = None
        
        logger.info(
            f"GrokService initialized: "
            f"max_rpm={self.max_requests_per_minute}, "
            f"max_concurrent={self.max_concurrent_requests}"
        )

    async def _wait_for_rate_limit(self):
        """Wait if we're approaching rate limits"""
        now = datetime.utcnow()
        
        # Clean old request times (older than 1 minute)
        self.request_times = [t for t in self.request_times if now - t < timedelta(minutes=1)]
        
        # If we're at the limit, wait
        if len(self.request_times) >= self.max_requests_per_minute:
            oldest_request = min(self.request_times)
            wait_until = oldest_request + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            if wait_seconds > 0:
                logger.warning(f"Rate limit approaching, waiting {wait_seconds:.1f}s")
                await asyncio.sleep(wait_seconds)
        
        # Check if we're in a rate limit cooldown period
        if self.rate_limit_reset_at and now < self.rate_limit_reset_at:
            wait_seconds = (self.rate_limit_reset_at - now).total_seconds()
            logger.warning(f"Rate limited, waiting until {self.rate_limit_reset_at}")
            await asyncio.sleep(wait_seconds)
            self.rate_limit_reset_at = None
    
    def _parse_rate_limit_headers(self, response_headers: Dict[str, Any]) -> Optional[datetime]:
        """Parse rate limit headers from API response"""
        # Common rate limit headers (OpenAI-compatible)
        reset_header = response_headers.get("x-ratelimit-reset-requests") or \
                      response_headers.get("x-ratelimit-reset")
        
        if reset_header:
            try:
                # Could be Unix timestamp or ISO format
                if isinstance(reset_header, (int, float)):
                    return datetime.fromtimestamp(reset_header)
                else:
                    return datetime.fromisoformat(reset_header.replace('Z', '+00:00'))
            except Exception:
                pass
        
        return None
    
    async def chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        output_schema: Optional[type[BaseModel]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send chat completion request to Grok API with rate limit handling

        Args:
            system_prompt: System prompt for the agent
            user_message: User message/question
            output_schema: Pydantic model for structured output (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            tools: List of tool definitions for function calling (MCP tools)
            tool_choice: Tool choice mode ("auto", "none", or {"type": "function", "function": {"name": "tool_name"}})

        Returns:
            Dict with 'content', 'prompt_tokens', 'completion_tokens', 'total_tokens'
        
        Raises:
            RateLimitError: If rate limit exceeded after all retries
            APIError: For other API errors
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

        # Add tools if provided (for MCP/function calling)
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

        # Add structured output if schema provided (only if no tools)
        if output_schema and not tools:
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
            message = response.choices[0].message

            result = {
                "content": message.content,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

            # Include tool calls if present
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]

            return result
        except Exception as e:
            raise Exception(f"Grok API error: {str(e)}")

    async def chat_completion_with_messages(
        self,
        messages: list[Dict[str, Any]],
        output_schema: Optional[type[BaseModel]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        tools: Optional[list[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send chat completion with full message history (for multi-turn with tools)

        Args:
            messages: Full conversation history including system, user, assistant, and tool messages
            output_schema: Pydantic model for structured output (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            tools: List of tool definitions for function calling
            tool_choice: Tool choice mode

        Returns:
            Dict with 'content', 'prompt_tokens', 'completion_tokens', 'tool_calls' (if any)
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Add tools if provided
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

        # Add structured output if schema provided (only if no tools)
        if output_schema and not tools:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": output_schema.__name__,
                    "schema": output_schema.model_json_schema(),
                    "strict": True
                }
            }

        # Use semaphore to limit concurrent requests
        logger.info(f"[GROK API] Acquiring semaphore (max concurrent: {self.max_concurrent_requests})")
        async with self.semaphore:
            logger.info("[GROK API] Semaphore acquired")
            # Wait if approaching rate limits
            logger.info("[GROK API] Checking rate limits")
            await self._wait_for_rate_limit()
            
            # Retry loop with exponential backoff for rate limits
            last_exception = None
            for attempt in range(self.rate_limit_retry_attempts):
                logger.info(f"[GROK API] Attempt {attempt + 1}/{self.rate_limit_retry_attempts}")
                try:
                    # Record request time
                    self.request_times.append(datetime.utcnow())
                    logger.info(f"[GROK API] Making API call to {self.model}")
                    logger.info(f"[GROK API] Request kwargs: model={kwargs.get('model')}, max_tokens={kwargs.get('max_tokens')}")
                    
                    response = await self.client.chat.completions.create(**kwargs)
                    logger.info("[GROK API] API call successful")
                    
                    # Parse rate limit headers if available
                    if hasattr(response, 'headers'):
                        reset_time = self._parse_rate_limit_headers(response.headers)
                        if reset_time:
                            self.rate_limit_reset_at = reset_time

                    return {
                        "content": response.choices[0].message.content,
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                    
                except RateLimitError as e:
                    last_exception = e
                    logger.warning(f"Rate limit error (attempt {attempt + 1}/{self.rate_limit_retry_attempts}): {e}")
                    
                    # Calculate backoff delay with jitter
                    # Exponential backoff: base * 2^attempt + random jitter
                    base_delay = self.base_retry_delay * (2 ** attempt)
                    jitter = random.uniform(0, 1)  # Random jitter up to 1 second
                    delay = base_delay + jitter
                    
                    # Cap delay at 60 seconds
                    delay = min(delay, 60.0)
                    
                    logger.info(f"Retrying after {delay:.1f}s (exponential backoff)")
                    await asyncio.sleep(delay)
                    
                    # Try to parse retry-after header if available
                    if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                        retry_after = e.response.headers.get('retry-after')
                        if retry_after:
                            try:
                                retry_seconds = int(retry_after)
                                self.rate_limit_reset_at = datetime.utcnow() + timedelta(seconds=retry_seconds)
                                logger.info(f"Rate limit resets in {retry_seconds}s")
                            except ValueError:
                                pass
                    
                    continue
                    
                except APIError as e:
                    # For other API errors, raise immediately (don't retry)
                    logger.error(f"Grok API error: {e}")
                    raise Exception(f"Grok API error: {str(e)}") from e
                    
                except Exception as e:
                    # Unexpected errors
                    logger.error(f"Unexpected error calling Grok API: {e}")
                    raise Exception(f"Grok API error: {str(e)}") from e
            
            # If we exhausted retries, raise the last exception
            if last_exception:
                raise Exception(
                    f"Rate limit exceeded after {self.rate_limit_retry_attempts} attempts. "
                    f"Please wait before retrying. Last error: {str(last_exception)}"
                ) from last_exception
            
            raise Exception("Unexpected error: retry loop completed without result")

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
