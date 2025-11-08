from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator, Optional
from agents import trace, gen_trace_id

TRACE_DASHBOARD = "https://platform.openai.com/traces/trace?trace_id="

def enable_tracing(enabled: bool = True) -> None:
    """
    Enable or disable tracing for the Agents SDK.
    This is a placeholder - actual tracing is controlled via environment variables.
    """
    if enabled:
        # Tracing is enabled via OPENAI_TRACING environment variable
        # The SDK will automatically use it if set
        pass

@contextmanager
def start_trace(name: str, trace_id: Optional[str] = None) -> Iterator[None]:
    """
    Opens an SDK trace context and prints a clickable link.
    Usage:
        with start_trace("Deep Research Pro"):
            ...
    """
    tid = trace_id or gen_trace_id()
    print(f"🔗 Trace: {TRACE_DASHBOARD}{tid}")
    with trace(name, trace_id=tid):
        yield
