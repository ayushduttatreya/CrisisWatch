"""Centralized OpenRouter client for AI intelligence layer."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, TypeVar, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from openai import AsyncOpenAI, APITimeoutError, APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar('T')


@dataclass
class AIResponse:
    """Structured AI response with metadata."""
    content: Optional[str]
    parsed_json: Optional[Dict]
    success: bool
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0


class OpenRouterClient:
    """Async OpenRouter client with retries, timeouts, and structured output handling."""
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = settings.OPENROUTER_MODEL
        self.timeout = settings.OPENROUTER_TIMEOUT
        self.max_concurrent = settings.OPENROUTER_MAX_CONCURRENT
        
        # Semaphore to limit concurrent AI calls
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Cache for AI responses (simple in-memory cache)
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=10)
        
        # Initialize async client
        self._client: Optional[AsyncOpenAI] = None
    
    async def _get_client(self) -> AsyncOpenAI:
        """Get or create async OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client
    
    def _get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key for a prompt."""
        return f"{model}:{hash(prompt)}"
    
    def _get_cached(self, cache_key: str) -> Optional[AIResponse]:
        """Get cached response if valid."""
        if cache_key not in self._cache:
            return None
        
        result, timestamp = self._cache[cache_key]
        if datetime.utcnow() - timestamp > self._cache_ttl:
            del self._cache[cache_key]
            return None
        
        return result
    
    def _set_cached(self, cache_key: str, response: AIResponse) -> None:
        """Cache an AI response."""
        self._cache[cache_key] = (response, datetime.utcnow())
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
        expect_json: bool = False,
        cache_key: Optional[str] = None,
    ) -> AIResponse:
        """
        Generate AI response with retries and timeout handling.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            expect_json: Whether to expect and parse JSON output
            cache_key: Optional cache key for deduplication
        
        Returns:
            AIResponse with content, parsed JSON, and metadata
        """
        start_time = asyncio.get_event_loop().time()
        
        # Check cache
        if cache_key:
            cached = self._get_cached(cache_key)
            if cached:
                logger.debug(f"Cache hit for key: {cache_key[:50]}...")
                return cached
        
        async with self._semaphore:
            try:
                client = await self._get_client()
                
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                
                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                content = response.choices[0].message.content
                tokens_used = response.usage.total_tokens if response.usage else 0
                
                # Parse JSON if expected
                parsed_json = None
                if expect_json and content:
                    try:
                        # Extract JSON from markdown code blocks if present
                        json_content = content
                        if "```json" in content:
                            json_content = content.split("```json")[1].split("```")[0]
                        elif "```" in content:
                            json_content = content.split("```")[1].split("```")[0]
                        
                        parsed_json = json.loads(json_content.strip())
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON response: {e}")
                
                result = AIResponse(
                    content=content,
                    parsed_json=parsed_json,
                    success=True,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                )
                
                # Cache successful response
                if cache_key:
                    self._set_cached(cache_key, result)
                
                logger.info(f"AI call completed: {latency_ms:.0f}ms, {tokens_used} tokens")
                return result
                
            except APITimeoutError:
                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.error(f"AI call timed out after {latency_ms:.0f}ms")
                return AIResponse(
                    content=None,
                    parsed_json=None,
                    success=False,
                    error="timeout",
                    latency_ms=latency_ms,
                )
                
            except APIError as e:
                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.error(f"AI API error: {e}")
                return AIResponse(
                    content=None,
                    parsed_json=None,
                    success=False,
                    error=f"api_error: {e}",
                    latency_ms=latency_ms,
                )
                
            except Exception as e:
                latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.error(f"Unexpected AI error: {e}")
                return AIResponse(
                    content=None,
                    parsed_json=None,
                    success=False,
                    error=f"unexpected: {e}",
                    latency_ms=latency_ms,
                )
    
    async def generate_batch(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.3,
        expect_json: bool = False,
    ) -> List[AIResponse]:
        """
        Generate multiple AI responses with concurrency control.
        
        Args:
            prompts: List of prompts to process
            system_prompt: Shared system prompt
            max_tokens: Max tokens per response
            temperature: Sampling temperature
            expect_json: Whether to expect JSON outputs
        
        Returns:
            List of AIResponse objects
        """
        tasks = [
            self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                expect_json=expect_json,
                cache_key=f"batch:{hash(prompt)}",
            )
            for prompt in prompts
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)


# Global client instance
_client: Optional[OpenRouterClient] = None


def get_client() -> OpenRouterClient:
    """Get or create OpenRouter client singleton."""
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client


async def generate_text(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> Optional[str]:
    """Convenience function to generate text."""
    response = await get_client().generate(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.content if response.success else None


async def generate_json(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 500,
    temperature: float = 0.3,
) -> Optional[Dict]:
    """Convenience function to generate structured JSON."""
    response = await get_client().generate(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        expect_json=True,
    )
    return response.parsed_json if response.success else None
