# app/core/safe.py
import logging
from agents import Runner

log = logging.getLogger("deep_research")

def setup_logging():
    if not log.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

def safe_run(agent, prompt, output_type):
    try:
        res = Runner.run_sync(agent, prompt)
        return res.final_output_as(output_type)
    except Exception as e:
        log.exception(f"[{agent.name}] failed")
        # re-raise so CLI/tests still fail loudly
        raise

async def safe_run_async(agent, prompt, output_type):
    """Async version of safe_run with consistent error handling."""
    try:
        res = await Runner.run(agent, prompt)
        return res.final_output_as(output_type)
    except Exception:
        agent_name = getattr(agent, "name", "agent")
        prompt_len = len(prompt or "")
        log.exception("[%s] failed on prompt len=%d", agent_name, prompt_len)
        # re-raise so CLI/tests still fail loudly
        raise

