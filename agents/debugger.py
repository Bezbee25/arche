"""Debugger agent: analyze error + suggest fix."""
from __future__ import annotations

from rich.console import Console

from core.plan_manager import get_spec
from core.router import call_llm
from core.session_logger import log

console = Console()


def run(plan_id: str, plan_meta: dict, error_message: str) -> str:
    """Analyze an error and suggest a fix."""
    spec = get_spec(plan_id)

    system_prompt = (
        "You are an expert debugger. "
        "Analyze the error, identify the root cause, and provide a concrete fix. "
        "Be systematic: 1) Root cause, 2) Fix, 3) How to verify."
    )

    prompt = f"""Project context:
{spec[:500] if spec else '(no spec)'}

Error to debug:
{error_message}

Provide:
1. Root cause analysis
2. Concrete fix (with code if applicable)
3. How to verify the fix works"""

    console.print(f"\n[bold red]Debugger[/bold red] — Analyzing error...\n")
    log(plan_id, f"Debug request: {error_message[:80]}", "DEBUG")

    result = call_llm(prompt, phase="debug", plan_meta=plan_meta, system=system_prompt, stream=True)
    return result
