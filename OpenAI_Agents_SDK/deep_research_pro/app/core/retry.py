"""
Retry utilities with exponential backoff for API calls.
Silently retries connection errors without logging.
Handles rate limit errors (429) with proper backoff.
"""

from __future__ import annotations
import asyncio
import random
import logging
import re
from typing import Callable, Awaitable, TypeVar
from openai import APIConnectionError, APITimeoutError, RateLimitError

T = TypeVar('T')

# Retry backoff times for connection errors
BACKOFFS = [0.5, 1.0, 2.0, 4.0]

# Rate limit backoff times (longer waits)
RATE_LIMIT_BACKOFFS = [2.0, 5.0, 10.0, 20.0, 30.0]

# Suppress OpenAI SDK connection error logs during retries
_openai_logger = logging.getLogger("openai")
_httpx_logger = logging.getLogger("httpx")


def _extract_retry_after(error_message: str) -> float:
    """Extract retry-after time from error message.
    
    Example: "Please try again in 10.908s" -> 10.908
    """
    match = re.search(r'try again in ([\d.]+)s', error_message, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


async def with_retry(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """
    Retry a coroutine with exponential backoff.
    Handles connection errors, timeouts, and rate limit errors.
    
    Args:
        coro_factory: A callable that returns an awaitable (coroutine)
        
    Returns:
        The result of the coroutine
        
    Raises:
        APIConnectionError, APITimeoutError, or RateLimitError if all retries fail
    """
    # Store original log levels
    original_openai_level = _openai_logger.level
    original_httpx_level = _httpx_logger.level
    
    rate_limit_attempts = 0
    
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
            
        except RateLimitError as e:
            # Restore log levels
            if i > 1:
                _openai_logger.setLevel(original_openai_level)
                _httpx_logger.setLevel(original_httpx_level)
            
            rate_limit_attempts += 1
            
            # Extract retry-after time from error message if available
            retry_after = None
            if hasattr(e, 'response') and e.response:
                retry_after = e.response.headers.get('retry-after')
                if retry_after:
                    try:
                        retry_after = float(retry_after)
                    except (ValueError, TypeError):
                        retry_after = None
            
            # If not in headers, try to extract from error message
            if retry_after is None and hasattr(e, 'message'):
                retry_after = _extract_retry_after(str(e.message))
            
            # Use extracted time or fall back to exponential backoff
            if retry_after:
                wait_time = retry_after + random.random() * 2.0  # Add jitter
            else:
                if rate_limit_attempts <= len(RATE_LIMIT_BACKOFFS):
                    wait_time = RATE_LIMIT_BACKOFFS[rate_limit_attempts - 1] + random.random() * 2.0
                else:
                    wait_time = 30.0 + random.random() * 10.0  # Cap at ~30s
            
            if rate_limit_attempts >= 5:  # Max 5 rate limit retries
                raise
            
            # Wait before retrying
            await asyncio.sleep(wait_time)
            continue  # Retry with same backoff index
            
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

