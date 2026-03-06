"""Documenter agent: generate documentation (Gemini for large context)."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console

from core.plan_manager import get_spec
from core.router import call_llm
from core.session_logger import log

console = Console()


def run(plan_id: str, plan_meta: dict, target_path: str = ".") -> str:
    """Generate documentation for the project or a specific path."""
    spec = get_spec(plan_id)

    # Gather source files if target is a directory
    source_context = _gather_source_context(target_path)

    prompt = f"""Generate comprehensive documentation for the following project.

Project spec:
{spec}

Source code context:
{source_context}

Generate:
1. Overview / README content
2. API documentation (if applicable)
3. Architecture description
4. Usage examples

Format as Markdown."""

    console.print(f"\n[bold yellow]Documenter[/bold yellow] — Generating documentation (phase: doc)...\n")
    log(plan_id, f"Doc generation for path: {target_path}", "DOC")

    result = call_llm(prompt, phase="doc", plan_meta=plan_meta, stream=True)
    return result


def _gather_source_context(path: str, max_chars: int = 50000) -> str:
    """Gather source files content, up to max_chars."""
    p = Path(path)
    if not p.exists():
        return "(path not found)"

    if p.is_file():
        return p.read_text()[:max_chars]

    # Directory: gather Python/JS/etc files
    extensions = {".py", ".js", ".ts", ".go", ".java", ".md"}
    content_parts = []
    total = 0

    for ext in extensions:
        for f in sorted(p.rglob(f"*{ext}")):
            if any(skip in str(f) for skip in ["node_modules", ".git", "__pycache__", "venv"]):
                continue
            try:
                text = f.read_text()
                header = f"\n\n### {f.relative_to(p)}\n```\n"
                footer = "\n```\n"
                content_parts.append(header + text[:2000] + footer)
                total += len(text)
                if total > max_chars:
                    content_parts.append("\n_(truncated — too many files)_")
                    break
            except Exception:
                pass

    return "".join(content_parts) if content_parts else "(no source files found)"
