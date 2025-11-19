# app/core/safe.py
from agents import Runner
from openai import RateLimitError
from app.core.retry import with_retry

async def safe_run_async(agent, prompt, output_type):
    """Async wrapper for Runner.run with error handling and rate limit retry."""
    
    async def _run_agent():
        """Inner function to run the agent (for retry wrapper)."""
        res = await Runner.run(agent, input=prompt)
        return res.final_output_as(output_type)
    
    # Use retry wrapper to handle rate limits and connection errors
    try:
        return await with_retry(_run_agent)
    except RateLimitError as e:
        # If retry logic exhausted, raise with helpful message
        raise RuntimeError(
            f"Rate limit exceeded. Please wait a moment and try again. "
            f"Original error: {str(e)}"
        ) from e

