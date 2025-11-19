"""
CLI entry point for Deep Research Pro.
Command-line interface for running research queries.
"""

from __future__ import annotations

import argparse
import asyncio
from rich import print
from pathlib import Path

from app.core.settings import PROJECT_NAME, OPENAI_API_KEY
from app.core.tracing import TRACE_DASHBOARD
from app.core.openai_client import make_async_client
from app.core.research_manager import ResearchManager
from agents import trace, gen_trace_id

# Ensure OPENAI_API_KEY is in environment for Agents SDK
if OPENAI_API_KEY and not __import__("os").environ.get("OPENAI_API_KEY"):
    __import__("os").environ["OPENAI_API_KEY"] = OPENAI_API_KEY


async def main_async():
    parser = argparse.ArgumentParser(description="Deep Research Pro — CLI")
    parser.add_argument("--topic", type=str, required=True, help="Research topic/query")
    parser.add_argument("--num-searches", type=int, default=5, help="Number of search queries (default: 5)")
    parser.add_argument("--num-sources", type=int, default=8, help="Max sources to return (default: 8)")
    parser.add_argument("--max-waves", type=int, default=3, help="Maximum research waves/iterations (default: 3)")
    parser.add_argument("--output", type=str, help="Output file path (optional, saves markdown)")
    args = parser.parse_args()

    print(f"[bold cyan]{PROJECT_NAME}[/bold cyan] • CLI Mode")
    print(":key: OPENAI_API_KEY detected" if OPENAI_API_KEY else ":warning: OPENAI_API_KEY not set")

    if not OPENAI_API_KEY:
        print("[bold red]Error:[/bold red] OPENAI_API_KEY not set. Please set it in your .env file.")
        return

    # Generate trace ID
    trace_id = gen_trace_id()
    trace_url = f"{TRACE_DASHBOARD}{trace_id}"
    print(f"🔗 Trace: {trace_url}")

    # Create ResearchManager
    manager = ResearchManager(
        openai_client=make_async_client(),
        num_searches=args.num_searches,
        num_sources=args.num_sources,
        max_waves=args.max_waves,
    )

    print(f"\n[bold]Research Query:[/bold] {args.topic}")
    print(f"[bold]Number of Searches:[/bold] {args.num_searches}")
    print(f"[bold]Max Sources:[/bold] {args.num_sources}")
    print(f"[bold]Max Waves:[/bold] {args.max_waves}\n")

    with trace("Research trace", trace_id=trace_id):
        # Run research pipeline
        async for report_md, status, analytics in manager.run(args.topic):
            # Print status updates
            if status:
                print(f"[dim]{status}[/dim]")
            
            # When complete, report_md will contain the final markdown
            if report_md:
                print("\n" + "="*80)
                print("[bold green]Research Report[/bold green]")
                print("="*80 + "\n")
                print(report_md)
                
                # Save to file if requested
                if args.output:
                    output_path = Path(args.output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(report_md, encoding="utf-8")
                    print(f"\n[bold green]💾 Saved to {output_path.resolve()}[/bold green]")
                
                # Sources are now in the References section of the report, no need to print separately


def main():
    """Entry point for CLI."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

