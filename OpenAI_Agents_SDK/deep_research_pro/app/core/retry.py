"""
Retry utilities with exponential backoff for API calls.
Silently retries connection errors without logging.
"""

from __future__ import annotations
import asyncio
import random
import logging
from typing import Callable, Awaitable, TypeVar
from openai import APIConnectionError, APITimeoutError

T = TypeVar('T')

# Retry backoff times
BACKOFFS = [0.5, 1.0, 2.0, 4.0]

# Suppress OpenAI SDK connection error logs during retries
_openai_logger = logging.getLogger("openai")
_httpx_logger = logging.getLogger("httpx")


async def with_retry(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """
    Retry a coroutine with exponential backoff.
    Silently retries connection errors without logging to console.
    
    Args:
        coro_factory: A callable that returns an awaitable (coroutine)
        
    Returns:
        The result of the coroutine
        
    Raises:
        APIConnectionError or APITimeoutError if all retries fail
    """
    # Store original log levels
    original_openai_level = _openai_logger.level
    original_httpx_level = _httpx_logger.level
    
    for i, b in enumerate(BACKOFFS, 1):
        try:
            # Suppress error logs during retries (not first attempt)
            if i > 1:
                _openai_logger.setLevel(logging.CRITICAL)
                _httpx_logger.setLevel(logging.CRITICAL)
            
            result = await coro_factory()
            
            # Restore log levels on success
            if i > 1:
                _openai_logger.setLevel(original_openai_level)
                _httpx_logger.setLevel(original_httpx_level)
            
            return result
            
        except (APIConnectionError, APITimeoutError):
            # Restore log levels before retry
            if i > 1:
                _openai_logger.setLevel(original_openai_level)
                _httpx_logger.setLevel(original_httpx_level)
            
            if i == len(BACKOFFS):
                # Final attempt failed - restore logs and raise
                raise
            
            # Silent retry - don't log connection errors during retries
            await asyncio.sleep(b + random.random() * 0.25)
    
    # This should never be reached, but type checker needs it
    raise RuntimeError("Retry logic failed unexpectedly")

