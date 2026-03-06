"""Analyst agent: interactive questions → spec.md"""
from __future__ import annotations

from rich.console import Console
from rich.prompt import Prompt

from core.track_manager import get_spec, save_spec, update_track_phase
from core.router import call_llm
from core.session_logger import log

console = Console()

REFINE_PROMPT = """You are a senior software architect. A developer has provided a rough project spec below.

Your task: rewrite it as a clear, detailed, professional spec document.
Constraints:
- Work ONLY from the information provided — do not add requirements the developer did not mention
- Expand and clarify each point: turn vague statements into precise, actionable requirements
- Add acceptance criteria for each requirement where relevant
- Resolve ambiguities using the most reasonable interpretation
- Keep the same scope — do not expand or reduce it

Output a complete spec in Markdown with these sections (include only those with content):
- ## Goal — one clear sentence describing the objective
- ## Context — background, existing systems, relevant technical constraints
- ## Requirements — numbered list, each with clear acceptance criteria
- ## Constraints — technical constraints, forbidden approaches, performance targets
- ## Out of Scope — what is explicitly excluded

Raw spec from developer:
{spec}

Output only the complete refined Markdown spec, starting with # Spec:"""

INTERVIEW_PROMPT = """You are a senior software architect conducting a requirements interview.

Developer's initial description:
{description}

{history_section}

Your task:
- If you need more information, ask EXACTLY ONE clear, specific question. Output only the question (no preamble, no "Question:" prefix).
- If you have enough information (typically after 2-5 exchanges, or if the description is already detailed enough), write the complete spec.

When writing the spec, start with "# Spec:" on the first line and include:
- ## Goal — one clear sentence
- ## Context — relevant background (if any)
- ## Requirements — numbered list, each with acceptance criteria
- ## Constraints — forbidden approaches, performance targets (if any)
- ## Out of Scope — explicitly excluded (if any)

Rules:
- Use ONLY information provided by the developer — never invent requirements
- Ask targeted questions: goal clarity, technical context, constraints, edge cases
- After 5 questions, always write the spec with available information

Output either a single question OR the complete spec starting with "# Spec:"."""

SPEC_QUESTIONS = [
    ("goal", "What is the main goal of this plan? (one sentence)"),
    ("context", "What is the existing context / codebase this relates to?"),
    ("requirements", "List the key requirements or acceptance criteria (one per line, empty line to finish):"),
    ("constraints", "Any technical constraints, forbidden approaches, or performance targets?"),
    ("out_of_scope", "What is explicitly OUT OF SCOPE?"),
]


def run_interactive(track_id: str, track_name: str, auto_refine: bool = True) -> str:
    """Run interactive Q&A to generate a spec.md, then refine it with LLM unless auto_refine=False."""
    console.print(f"\n[bold cyan]Analyst[/bold cyan] — Building spec for: [bold]{track_name}[/bold]\n")
    console.print("[dim]Answer the following questions to define the track scope.[/dim]\n")

    answers = {}
    for key, question in SPEC_QUESTIONS:
        console.print(f"[yellow]{question}[/yellow]")
        if key == "requirements":
            lines = []
            while True:
                line = input("  > ").strip()
                if not line:
                    break
                lines.append(f"- {line}")
            answers[key] = "\n".join(lines) if lines else "- (none specified)"
        else:
            answer = Prompt.ask("  >", default="(skip)")
            answers[key] = answer

    spec = _build_spec(track_name, answers)
    save_spec(track_id, spec)
    update_track_phase(track_id, "plan")
    log(track_id, f"Spec generated for track '{track_name}'", "ANALYST")
    console.print("\n[green]✓ Spec saved.[/green]")

    if auto_refine:
        console.print("\n[dim]Refining spec with LLM...[/dim]")
        from core.track_manager import load_project
        track_meta = {"id": track_id, "name": track_name}
        spec = refine_with_llm(track_id, track_meta)

    return spec


def refine_with_llm(track_id: str, track_meta: dict, additional_context: str = "") -> str:
    """Use LLM to refine/expand the spec based on existing draft."""
    current_spec = get_spec(track_id)

    prompt = f"""You are a software architect. Review and refine the following project spec.
Make it more precise, add missing acceptance criteria, clarify ambiguities.
Output the complete improved spec in Markdown format.

Current spec:
{current_spec}

{f'Additional context: {additional_context}' if additional_context else ''}

Output only the refined Markdown spec, starting with # Spec: ..."""

    console.print("\n[bold cyan]Analyst[/bold cyan] — Refining spec with LLM...\n")
    refined = call_llm(prompt, phase="spec", track_meta=track_meta, stream=True)
    save_spec(track_id, refined)
    log(track_id, "Spec refined via LLM", "ANALYST")
    console.print("\n[green]✓ Spec refined and saved.[/green]")
    return refined


def _build_spec(track_name: str, answers: dict) -> str:
    lines = [f"# Spec: {track_name}\n"]

    if answers.get("goal"):
        lines += [f"## Goal\n\n{answers['goal']}\n"]

    if answers.get("context") and answers["context"] != "(skip)":
        lines += [f"## Context\n\n{answers['context']}\n"]

    if answers.get("requirements"):
        lines += [f"## Requirements\n\n{answers['requirements']}\n"]

    if answers.get("constraints") and answers["constraints"] != "(skip)":
        lines += [f"## Constraints\n\n{answers['constraints']}\n"]

    if answers.get("out_of_scope") and answers["out_of_scope"] != "(skip)":
        lines += [f"## Out of Scope\n\n{answers['out_of_scope']}\n"]

    lines += ["## Tasks\n\n_(To be generated by planner)_\n"]

    return "\n".join(lines)
