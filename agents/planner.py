"""Planner agent: spec.md → tasks.yaml"""
from __future__ import annotations

import re

from rich.console import Console

from core.track_manager import get_spec, save_spec, update_track_meta, update_track_phase
from core.router import call_llm
from core.session_logger import log
from core.task_engine import add_tasks_bulk, load_tasks

console = Console()

PHASE_PLANNER_PROMPT = """You are a software architect. From the spec below, identify the distinct development phases.

Spec:
{spec}

A phase is a major logical grouping of work (e.g. "Database Schema", "REST API", "Frontend", "Tests", "DevOps").

Rules:
- Each phase should be independently deliverable
- Identify dependencies: which phase must complete before another can start
- Aim for 2-6 phases; don't over-granularize

Output ONLY a numbered list in this exact format:
1. Phase Name | depends_on: none
   Description: one sentence describing the phase scope
2. Phase Name | depends_on: 1
   Description: one sentence
3. Phase Name | depends_on: 1, 2
   Description: one sentence

Output the phase list now:"""

PHASE_TASK_PLANNER_PROMPT = """You are a software project planner. Generate tasks for the following development phase.

Plan spec:
{spec}

Phase: {phase_name}
Phase description: {phase_description}

Generate ONLY tasks for this specific phase. Each task should be:
- Completable in 1-4 hours
- Ordered logically (dependencies first)
- Specific and actionable
- Scoped to this phase only

Output ONLY a numbered list in this exact format:
1. Task title here
   Description: brief description of what needs to be done

2. Another task
   Description: what to implement

Output the task list now:"""

PLANNER_PROMPT = """You are a software project planner. Given the following spec, decompose the work into concrete, actionable development tasks.

Rules:
- Each task should be completable in 1-4 hours
- Tasks should be ordered logically (dependencies first)
- Be specific, not vague
- Output ONLY a numbered list in this exact format:

1. Task title here
   Description: brief description of what needs to be done

2. Another task title
   Description: what to implement

...

Spec:
{spec}

Output the task list now:"""


def generate_tasks_from_template(
    track_id: str, track_meta: dict, description: str, subtypes: list[str]
) -> list[dict]:
    """Generate template tasks instantly (no LLM) for task/debug track types."""
    track_type = track_meta.get("track_type", "task")
    name = track_meta.get("name", "")

    # Save description as spec
    spec = f"# Spec: {name}\n\n## Description\n\n{description}\n"
    save_spec(track_id, spec)

    if track_type == "debug":
        tasks = [
            {"title": "Investigate root cause", "description": f"Reproduce and identify the root cause of: {description}"},
            {"title": "Implement fix", "description": "Apply the fix based on the investigation findings"},
        ]
        if "regression" in subtypes:
            tasks.append({"title": "Add regression test", "description": "Write a test that catches this bug to prevent future regressions"})
    else:
        # task type
        tasks = [
            {"title": f"Implement: {name}", "description": description},
        ]
        if "test" in subtypes:
            tasks.append({"title": "Write tests", "description": f"Write tests covering the implementation of: {description}"})
        if "doc" in subtypes:
            tasks.append({"title": "Update documentation", "description": f"Update docs/README to reflect changes for: {description}"})

    new_tasks = add_tasks_bulk(track_id, tasks)
    update_track_phase(track_id, "dev")
    log(track_id, f"Generated {len(new_tasks)} template tasks ({track_type})", "PLANNER")
    return new_tasks


def generate_tasks(track_id: str, track_meta: dict) -> list[dict]:
    """Use LLM to generate tasks from spec, then save them."""
    spec = get_spec(track_id)
    if not spec or spec.strip() == f"# Spec: {track_meta.get('name', '')}\n\n":
        console.print("[yellow]Warning: spec is empty. Run 'arche spec' first.[/yellow]")
        return []

    console.print("\n[bold blue]Planner[/bold blue] — Generating tasks from spec...\n")

    prompt = PLANNER_PROMPT.format(spec=spec)
    output = call_llm(prompt, phase="plan", track_meta=track_meta, stream=True)

    tasks = _parse_task_list(output)
    if not tasks:
        console.print("[yellow]Could not parse tasks from LLM output. Add tasks manually.[/yellow]")
        return []

    # Only add tasks if there are none yet (avoid duplicates on re-run)
    existing = load_tasks(track_id)
    if existing:
        console.print(f"[yellow]{len(existing)} tasks already exist. Skipping generation.[/yellow]")
        return existing

    new_tasks = add_tasks_bulk(track_id, tasks)
    update_track_phase(track_id, "dev")
    log(track_id, f"Generated {len(new_tasks)} tasks via planner", "PLANNER")

    console.print(f"\n[green]✓ {len(new_tasks)} tasks created.[/green]")
    return new_tasks


def generate_tasks_from_spec_text(track_id: str, track_meta: dict, spec_text: str) -> list[dict]:
    """Generate tasks from provided spec text (used after analyst)."""
    console.print("\n[bold blue]Planner[/bold blue] — Generating tasks from spec...\n")

    prompt = PLANNER_PROMPT.format(spec=spec_text)
    output = call_llm(prompt, phase="plan", track_meta=track_meta, stream=True)

    tasks = _parse_task_list(output)
    if not tasks:
        return []

    new_tasks = add_tasks_bulk(track_id, tasks)
    update_track_phase(track_id, "dev")
    log(track_id, f"Generated {len(new_tasks)} tasks via planner", "PLANNER")
    console.print(f"\n[green]✓ {len(new_tasks)} tasks created.[/green]")
    return new_tasks


def _parse_phase_list(text: str) -> list[dict]:
    """Parse numbered phase list. Returns list of {name, description, depends_on_indices}."""
    phases = []
    lines = text.strip().split("\n")
    current = None

    for line in lines:
        m = re.match(r"^\s*\d+[.)]\s+([^|]+?)(?:\s*\|\s*depends_on:\s*(.*))?$", line, re.IGNORECASE)
        if m:
            if current:
                phases.append(current)
            name = m.group(1).strip()
            deps_str = (m.group(2) or "").strip().lower()
            dep_nums = []
            if deps_str and deps_str not in ("none", "(none)", ""):
                dep_nums = [d.strip() for d in re.split(r"[\s,]+", deps_str) if d.strip().isdigit()]
            current = {"name": name, "description": "", "depends_on_indices": dep_nums}
        elif current:
            dm = re.match(r"^\s+Description:\s*(.+)$", line, re.IGNORECASE)
            if dm:
                current["description"] = dm.group(1).strip()

    if current:
        phases.append(current)
    return phases


def _parse_task_list(text: str) -> list[dict]:
    """Parse numbered task list from LLM output."""
    tasks = []
    lines = text.strip().split("\n")

    current_title = None
    current_desc = []

    for line in lines:
        # Match numbered item: "1. Title" or "1) Title"
        match = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if match:
            if current_title:
                tasks.append({
                    "title": current_title,
                    "description": " ".join(current_desc).strip(),
                })
            current_title = match.group(1).strip()
            current_desc = []
        elif current_title and re.match(r"^\s+Description:\s*(.+)$", line, re.IGNORECASE):
            desc_match = re.match(r"^\s+Description:\s*(.+)$", line, re.IGNORECASE)
            current_desc.append(desc_match.group(1).strip())
        elif current_title and line.strip() and not re.match(r"^\s*\d+[.)]", line):
            # Continuation line for description
            stripped = line.strip()
            if stripped.startswith("Description:"):
                stripped = stripped[len("Description:"):].strip()
            if stripped:
                current_desc.append(stripped)

    if current_title:
        tasks.append({
            "title": current_title,
            "description": " ".join(current_desc).strip(),
        })

    return tasks
