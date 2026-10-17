# app/core/safe.py
from agents import Runner

async def safe_run_async(agent, prompt, output_type):
    """Async wrapper for Runner.run with error handling."""
    res = await Runner.run(agent, input=prompt)
    return res.final_output_as(output_type)

