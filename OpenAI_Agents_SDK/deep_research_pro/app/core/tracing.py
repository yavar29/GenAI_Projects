from __future__ import annotations
import os

def enable_tracing() -> None:
    """
    Minimal switch for OpenAI Traces. We keep it off by default to avoid surprises.
    Turn this on in later iterations by setting envs here.
    """
    # Example (commented for now):
    # os.environ["OPENAI_TRACING"] = "1"
    # os.environ["OPENAI_TRACE_SAMPLE_RATE"] = "1.0"
    pass
