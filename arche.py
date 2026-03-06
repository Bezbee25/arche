#!/usr/bin/env python3
"""arche — Development orchestrator CLI."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

app = typer.Typer(
    name="arche",
    help="arche — Multi-plan development orchestrator",
    no_args_is_help=False,
    invoke_without_command=True,
)
track_app = typer.Typer(help="Manage development tracks", no_args_is_help=True)
task_app = typer.Typer(help="Manage tasks within the active track", no_args_is_help=True)
spec_app = typer.Typer(help="Manage the spec of the active track", no_args_is_help=True)
app.add_typer(track_app, name="track")
app.add_typer(task_app, name="task")
app.add_typer(spec_app, name="spec")

console = Console()


def _require_project() -> dict:
    from core.track_manager import load_project, PROJECT_FILE
    project = load_project()
    if not project:
        console.print("[red]No project found.[/red] Run [bold]arche init[/bold] first.")
        raise typer.Exit(1)
    return project


def _require_active_track() -> dict:
    from core.track_manager import get_active_track
    plan = get_active_track()
    if not plan:
        console.print("[red]No active track.[/red] Use [bold]arche track new <name>[/bold] or [bold]arche track switch <id>[/bold].")
        raise typer.Exit(1)
    return plan


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """arche — Multi-plan development orchestrator."""
    if ctx.invoked_subcommand is None:
        from core.track_manager import PROJECT_FILE
        if PROJECT_FILE.exists():
            from core.status import show_resume
            show_resume()
        else:
            _show_help()


@app.command(name="help")
def help_cmd() -> None:
    """Show the full command reference and usage guide."""
    _show_help()


def _show_help() -> None:
    from rich.padding import Padding
    from rich.rule import Rule
    from rich.table import Table

    c = console

    def cmd(text: str) -> str:
        return f"[bold white]{text}[/bold white]"

    def section(title: str, color: str, rows: list[tuple]) -> None:
        t = Table(show_header=False, box=None, padding=(0, 2), expand=False)
        t.add_column("cmd",  style=f"bold {color}", no_wrap=True, min_width=34)
        t.add_column("desc", style="dim white")
        for c1, c2 in rows:
            t.add_row(c1, c2)
        c.print(f"  [bold {color}]{title}[/bold {color}]")
        c.print(Padding(t, (0, 0, 1, 2)))

    # ── Header ────────────────────────────────────────────────────────────
    c.print()
    c.print(Rule("[bold cyan]arche[/bold cyan]  —  development orchestrator", style="cyan"))
    c.print()
    c.print(
        "  arche keeps your [bold]project context alive[/bold] between sessions.\n"
        "  It breaks work into [bold]Plans[/bold] and [bold]Tasks[/bold], then\n"
        "  [bold]runs each task[/bold] by automatically feeding the full context\n"
        "  (spec, architecture memory, history) to your LLM CLI ([cyan]claude[/cyan], [yellow]gemini[/yellow]…).\n"
        "  After each task it updates the [bold]architecture memory[/bold].",
        highlight=False,
    )

    # ── What arche task run does ──────────────────────────────────────────
    c.print()
    c.print(Rule("What  arche task run  does", style="dim"))
    c.print()
    c.print(
        "  When you run [bold yellow]arche task run[/bold yellow], arche:\n\n"
        "  [dim]1.[/dim]  Reads the [bold]current task[/bold] (title + description)\n"
        "  [dim]2.[/dim]  Assembles the [bold]full context[/bold]:\n"
        "       spec.md       ← plan goal and requirements\n"
        "       archi.md      ← architecture memory (updated after every task)\n"
        "       done tasks    ← what has already been completed\n"
        "       session log   ← notes from the current session\n"
        "  [dim]3.[/dim]  Calls [bold]claude / gemini via CLI[/bold] with that context\n"
        "  [dim]4.[/dim]  Extracts [bold]architecture notes[/bold] from the response → archi.md\n"
        "  [dim]5.[/dim]  Logs everything to the [bold]session journal[/bold]",
        highlight=False,
    )

    # ── Flow 1: single feature ────────────────────────────────────────────
    c.print()
    c.print(Rule("Flow 1 — Single feature (or doc, refactor…)", style="dim"))
    c.print()
    c.print("  [dim]# Once, from the arche source directory:[/dim]")
    c.print(f"  {cmd('make install-pipx')}\n")
    c.print("  [dim]# In your project:[/dim]")
    c.print(f"  {cmd('arche init')}                        [dim]← project name, stack, LLM model choices[/dim]")
    c.print(f"  {cmd('arche track new \"feat: JWT auth\"')}  [dim]← interactive spec Q&A → tasks generated[/dim]")
    c.print()
    c.print("  [dim]# Work loop (repeat until done):[/dim]")
    c.print(f"  {cmd('arche task run')}       [dim]← runs current task with full context → LLM[/dim]")
    c.print(f"  {cmd('arche task done')}      [dim]← mark done, move to next[/dim]")
    c.print(f"  {cmd('arche task run')}       [dim]← next task, context now includes previous work[/dim]")
    c.print(f"  [dim]...[/dim]")
    c.print(f"  {cmd('arche track done')}      [dim]← plan complete[/dim]")

    # ── Flow 2: multi-plan ────────────────────────────────────────────────
    c.print()
    c.print(Rule("Flow 2 — Multi-track (feature + urgent bug in parallel)", style="dim"))
    c.print()
    c.print(f"  {cmd('arche track new \"feat: JWT auth\"')}    [dim]← track is ACTIVE[/dim]")
    c.print(f"  {cmd('arche task run')}                       [dim]← working on feat[/dim]")
    c.print()
    c.print("  [dim]# Urgent bug comes in:[/dim]")
    c.print(f"  {cmd('arche track new \"debug: crash login\"')} [dim]← feat PAUSED, debug ACTIVE[/dim]")
    c.print(f"  {cmd('arche task run')}                        [dim]← debug context loaded automatically[/dim]")
    c.print(f"  {cmd('arche task done')}  {cmd('arche track done')}   [dim]← bug fixed[/dim]")
    c.print()
    c.print("  [dim]# Back to the feature:[/dim]")
    c.print(f"  {cmd('arche track switch feat')}   [dim]← resumes exactly where you left off[/dim]")
    c.print(f"  {cmd('arche task run')}            [dim]← feat context reloaded[/dim]")

    # ── Flow 3: debug ─────────────────────────────────────────────────────
    c.print()
    c.print(Rule("Flow 3 — Debug", style="dim"))
    c.print()
    c.print(f"  {cmd('arche track new \"debug: NullPointerException login\"')}")
    c.print(f"  {cmd('arche debug \"NullPointerException at UserService.java:42\"')}")
    c.print(f"                   [dim]← analyses the error with full project context[/dim]")
    c.print(f"  {cmd('arche task run')}   [dim]← implements the fix[/dim]")
    c.print(f"  {cmd('arche task done')}  {cmd('arche track done')}")

    # ── Command reference ─────────────────────────────────────────────────
    c.print()
    c.print(Rule("Command reference", style="dim"))
    c.print()

    section("Status", "green", [
        ("arche  (no argument)",          "Full status: active track + all tasks"),
        ("arche track list",               "All tracks with progress bars"),
        ("arche task list",               "All tasks in the active track"),
    ])

    section("Setup", "cyan", [
        ("arche init",                    "Configure project + choose LLM models per phase"),
        ("arche web  [--port 7331]",      "Web UI with embedded terminal"),
        ("arche help",                    "Show this guide"),
    ])

    section("Tracks", "blue", [
        ("arche track new \"<name>\"",               "★ Step 1: spec Q&A → task generation (all-in-one)"),
        ("arche track new \"<name>\" --skip-analyst", "  Skip Q&A, start with empty spec"),
        ("arche track new \"<name>\" --skip-planner", "  Skip task generation"),
        ("arche track list",                          "List all tracks with status"),
        ("arche track switch <name>",                 "Switch active track (saves current state)"),
        ("arche track plan",                        "Generate tasks from spec (run planner)"),
        ("arche track done",                          "Mark active track as complete"),
    ])

    section("Tasks  ← the main loop", "yellow", [
        ("arche task run",                  "★ Run current task with full context → LLM"),
        ("arche task run --auto-done",      "  Same + mark DONE automatically"),
        ("arche task next",                 "  Show next task (without running it)"),
        ("arche task done [--notes \"…\"]", "  Mark current task done, advance to next"),
        ("arche task block \"<reason>\"",   "  Mark current task as blocked"),
        ("arche task add \"<title>\"",      "  Add a task manually"),
    ])

    section("Spec  ← outside track new", "magenta", [
        ("arche spec qa",                 "Q&A interview → spec + LLM refinement"),
        ("arche spec qa --no-refine",     "  Q&A only, skip LLM refinement"),
        ("arche spec refine",             "  Refine existing spec with LLM"),
        ("arche spec show",               "  Display the current spec"),
        ("arche spec help",               "  Full spec command reference"),
    ])

    section("Agents  ← ad-hoc", "magenta", [
        ("arche dev \"<instruction>\"",   "Free-form coding request with full track context"),
        ("arche debug \"<error>\"",       "Analyse error + fix with track context"),
        ("arche doc [<path>]",            "Generate documentation (Gemini large context)"),
        ("arche log \"<note>\"",          "Add a manual note to the session journal"),
    ])

    # ── Files managed automatically ───────────────────────────────────────
    c.print(Rule("Files managed automatically", style="dim"))
    c.print()
    c.print(
        "  [dim]storage/plans/{plan-id}/[/dim]\n"
        "  [dim]├──[/dim] [bold]spec.md[/bold]      [dim]← plan goal and requirements[/dim]\n"
        "  [dim]├──[/dim] [bold cyan]archi.md[/bold cyan]     [dim]← architecture memory, updated after every task run[/dim]\n"
        "  [dim]├──[/dim] [bold]tasks.yaml[/bold]   [dim]← tasks, statuses, notes[/dim]\n"
        "  [dim]└──[/dim] [bold]sessions/[/bold]    [dim]← session journal {date}.md with all LLM output[/dim]",
        highlight=False,
    )
    c.print()
    c.print(
        "  [dim]The [/dim][bold cyan]archi.md[/bold cyan][dim] is the key: every [/dim][bold]arche task run[/bold]"
        "[dim] instructs the LLM to document\n"
        "  its decisions → context grows richer with each completed task.[/dim]",
        highlight=False,
    )
    c.print()
    c.print(Rule(style="dim"))
    c.print()


@app.command()
def init() -> None:
    """Initialize arche for the current project."""
    from core.track_manager import (
        PROJECT_FILE, STORAGE_DIR, TRACKS_DIR,
        load_project, save_project
    )
    from core.router import detect_available_clis, DEFAULT_MODELS

    # Models available per CLI
    CLI_MODELS: dict[str, list[tuple[str, str]]] = {
        "claude": [
            ("claude-opus-4-6",          "Opus 4.6    — most capable, best reasoning"),
            ("claude-sonnet-4-6",        "Sonnet 4.6  — fast, strong, recommended"),
            ("claude-haiku-4-5-20251001","Haiku 4.5   — fastest, cheapest"),
        ],
        "gemini": [
            ("gemini-2.0-flash",         "Flash 2.0   — fast, 1M token context"),
            ("gemini-2.0-pro",           "Pro 2.0     — most capable Gemini"),
            ("gemini-1.5-pro",           "Pro 1.5     — large context fallback"),
        ],
        "codex": [
            ("codex",                    "Codex       — OpenAI code model"),
        ],
    }

    console.print("\n[bold cyan]arche init[/bold cyan] — Project setup\n")

    existing = load_project()
    if existing:
        if not Confirm.ask(f"Project '{existing.get('name')}' already configured. Reconfigure?"):
            console.print("[dim]Aborted.[/dim]")
            return

    STORAGE_DIR.mkdir(exist_ok=True)
    TRACKS_DIR.mkdir(parents=True, exist_ok=True)

    name = Prompt.ask("Project name", default=Path.cwd().name)
    description = Prompt.ask("Short description", default="")
    stack = Prompt.ask("Stack / main languages", default="Python")

    # Detect available CLIs
    available_clis = detect_available_clis()
    console.print()
    if available_clis:
        console.print(f"[green]Detected CLIs:[/green] {', '.join(available_clis)}")
    else:
        console.print("[yellow]No LLM CLIs detected.[/yellow] Make sure claude/gemini/codex are in PATH.")
        console.print("[dim]Continuing with defaults — you can re-run arche init later.[/dim]")

    # Build the list of selectable models from detected CLIs only
    available_models: list[tuple[str, str]] = []
    for cli in available_clis:
        available_models.extend(CLI_MODELS.get(cli, []))

    def pick_model(phase: str, desc: str) -> str:
        default = DEFAULT_MODELS.get(phase, "claude-sonnet-4-6")
        if not available_models:
            return default

        console.print(f"\n  [bold]{phase}[/bold] — {desc}")
        for i, (model_id, label) in enumerate(available_models, 1):
            marker = "[green]●[/green]" if model_id == default else " "
            console.print(f"    {marker} [dim]{i}.[/dim] {model_id}  [dim]{label}[/dim]")

        default_idx = next(
            (i for i, (m, _) in enumerate(available_models, 1) if m == default),
            1,
        )
        while True:
            raw = Prompt.ask(f"  Choose [1-{len(available_models)}]", default=str(default_idx))
            if raw.isdigit() and 1 <= int(raw) <= len(available_models):
                return available_models[int(raw) - 1][0]
            console.print(f"  [red]Enter a number between 1 and {len(available_models)}.[/red]")

    console.print("\n[bold]Model selection per phase[/bold] (Enter to keep default)\n")

    phase_descriptions = {
        "spec":   "Spec / deep thinking     — used by arche spec qa + refine",
        "plan":   "Planning / architecture  — used by arche track plan",
        "dev":    "Code generation          — used by arche task run",
        "debug":  "Debugging                — used by arche debug",
        "doc":    "Documentation            — used by arche doc",
        "review": "Code review              — used internally after task runs",
    }

    models = {}
    for phase, desc in phase_descriptions.items():
        models[phase] = pick_model(phase, desc)

    project_data = {
        "name": name,
        "description": description,
        "stack": stack,
        "models": models,
        "available_clis": available_clis,
    }

    save_project(project_data)

    console.print(f"\n[green]✓ Project '{name}' configured.[/green]")
    console.print("\n  Models selected:")
    for phase, model in models.items():
        console.print(f"    [dim]{phase:8}[/dim] {model}")
    console.print("\n  Run [bold]arche track new \"feat: something\"[/bold] to start.")


@app.command()
def scan() -> None:
    """Scan the project files and generate storage/archi.md via LLM (review model)."""
    _require_project()
    from core.scanner import run_scan
    run_scan()


@app.command()
def resume() -> None:
    """Show current state: active track, tasks, other plans."""
    _require_project()
    from core.status import show_resume
    show_resume()


@app.command()
def log(message: str = typer.Argument(..., help="Note to add to the session journal")) -> None:
    """Add a manual note to the active track's session journal."""
    _require_project()
    plan = _require_active_track()
    from core.session_logger import log as slog
    slog(plan["id"], message, "NOTE")
    console.print(f"[green]✓ Note logged.[/green]")


# ── Spec subcommands ─────────────────────────────────────────────────────────

@spec_app.command("help")
def spec_help() -> None:
    """Show spec command reference."""
    from rich.padding import Padding
    from rich.rule import Rule
    from rich.table import Table

    console.print()
    console.print(Rule("[bold magenta]arche spec[/bold magenta]  —  spec management", style="magenta"))
    console.print()
    t = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    t.add_column("cmd",  style="bold magenta", no_wrap=True, min_width=38)
    t.add_column("desc", style="dim white")
    t.add_row("arche spec qa",             "★ Q&A interview → spec, then LLM refinement")
    t.add_row("arche spec qa --no-refine", "  Q&A only, skip LLM refinement")
    t.add_row("arche spec refine",         "  Refine existing spec with LLM (no Q&A)")
    t.add_row("arche spec show",           "  Display the current spec")
    console.print(Padding(t, (0, 0, 1, 2)))
    console.print(Rule(style="dim"))
    console.print()


@spec_app.command("qa")
def spec_qa(
    no_refine: bool = typer.Option(False, "--no-refine", help="Skip LLM refinement after Q&A"),
) -> None:
    """Run Q&A interview to build the spec, then refine it with LLM."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]
    from agents.analyst import run_interactive
    run_interactive(track_id, plan.get("name", track_id), auto_refine=not no_refine)


@spec_app.command("refine")
def spec_refine() -> None:
    """Refine the existing spec with LLM (no Q&A)."""
    _require_project()
    plan = _require_active_track()
    from agents.analyst import refine_with_llm
    refine_with_llm(plan["id"], plan)


@spec_app.command("show")
def spec_show() -> None:
    """Display the current spec."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]
    from core.track_manager import get_spec
    from rich.markdown import Markdown
    from rich.rule import Rule
    content = get_spec(track_id)
    if not content or not content.strip():
        console.print("[yellow]No spec yet.[/yellow] Run [bold]arche spec qa[/bold] to create one.")
        return
    console.print(Rule(f"[bold]spec — {plan.get('name', track_id)}[/bold]", style="cyan"))
    console.print(Markdown(content))
    console.print(Rule(style="dim"))


@app.command()
def dev(instruction: str = typer.Argument(..., help="What to implement")) -> None:
    """Delegate a coding task to the LLM (with full plan context)."""
    _require_project()
    plan = _require_active_track()
    from agents.developer import run
    run(plan["id"], plan, instruction)


@app.command()
def debug(
    error: str = typer.Argument(..., help="Error message or description of the bug"),
) -> None:
    """Analyze an error and get a fix suggestion."""
    _require_project()
    plan = _require_active_track()
    from agents.debugger import run
    run(plan["id"], plan, error)


@app.command()
def doc(
    path: str = typer.Argument(".", help="Path to document (file or directory)"),
) -> None:
    """Generate documentation for the project."""
    _require_project()
    plan = _require_active_track()
    from agents.documenter import run
    run(plan["id"], plan, path)


@app.command()
def web(
    port: int = typer.Option(7331, help="Port to run the web server on"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
) -> None:
    """Start the web UI server."""
    _require_project()
    import subprocess
    import time
    import webbrowser

    console.print(f"\n[bold cyan]arche web[/bold cyan] — Starting server on port {port}\n")

    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed.[/red] Run: pip install uvicorn fastapi")
        raise typer.Exit(1)

    url = f"http://localhost:{port}"
    console.print(f"[green]→[/green] {url}")

    if not no_browser:
        # Open browser after slight delay
        import threading
        def _open():
            time.sleep(1.5)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    # Import and run the server
    from web.server import create_app
    uvicorn_app = create_app()

    import uvicorn
    uvicorn.run(uvicorn_app, host="0.0.0.0", port=port, log_level="warning")


# ── Plan subcommands ─────────────────────────────────────────────────────────

@track_app.command("help")
def track_help() -> None:
    """Show track command reference."""
    from rich.padding import Padding
    from rich.rule import Rule
    from rich.table import Table

    console.print()
    console.print(Rule("[bold blue]arche track[/bold blue]  —  track management", style="blue"))
    console.print()

    t = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    t.add_column("cmd",  style="bold blue", no_wrap=True, min_width=46)
    t.add_column("desc", style="dim white")
    t.add_row("arche track new \"<name>\"",               "★ Step 1: spec Q&A → task generation (all-in-one)")
    t.add_row("arche track new \"<name>\" --skip-analyst", "  Skip Q&A, start with empty spec")
    t.add_row("arche track new \"<name>\" --skip-planner", "  Skip task generation")
    t.add_row("arche track list",                          "List all tracks with status")
    t.add_row("arche track switch <id>",                   "Switch active track (saves current state)")
    t.add_row("arche track plan",                          "Generate tasks from spec (run planner)")
    t.add_row("arche track plan --force",                  "  Regenerate tasks (clears existing)")
    t.add_row("arche track done",                          "Mark active track as complete")
    console.print(Padding(t, (0, 0, 1, 2)))
    console.print(Rule(style="dim"))
    console.print()


@track_app.command("new")
def track_new(
    name: str = typer.Argument(..., help="Track name, e.g. 'feat: JWT auth'"),
    skip_analyst: bool = typer.Option(False, "--skip-analyst", help="Skip interactive spec creation"),
    skip_planner: bool = typer.Option(False, "--skip-planner", help="Skip task generation"),
    no_refine: bool = typer.Option(False, "--no-refine", help="Skip LLM spec refinement after Q&A"),
) -> None:
    """Create a new track and launch the analyst → planner flow."""
    _require_project()
    from core.track_manager import new_track
    from core.session_logger import log as slog

    plan = new_track(name)
    track_id = plan["id"]
    console.print(f"\n[green]✓ Track created:[/green] [bold]{name}[/bold] (id: {track_id})")

    spec_content = None
    if not skip_analyst:
        from agents.analyst import run_interactive
        spec_content = run_interactive(track_id, name, auto_refine=not no_refine)

    if not skip_planner and spec_content:
        from agents.planner import generate_tasks_from_spec_text
        generate_tasks_from_spec_text(track_id, plan, spec_content)
    elif not skip_planner:
        from agents.planner import generate_tasks
        generate_tasks(track_id, plan)

    slog(track_id, f"Track '{name}' created", "INIT")

    from core.status import show_resume
    show_resume()


@track_app.command("list")
def track_list() -> None:
    """List all tracks."""
    _require_project()
    from core.status import show_track_list
    show_track_list()


@track_app.command("switch")
def track_switch(
    name: str = typer.Argument(..., help="Track id, prefix, or name substring"),
) -> None:
    """Switch to a different track."""
    _require_project()
    from core.track_manager import switch_track
    from core.session_logger import log as slog

    current_plan = None
    try:
        current_plan = _require_active_track()
    except SystemExit:
        pass

    plan = switch_track(name)
    if not plan:
        console.print(f"[red]Track not found:[/red] {name}")
        console.print("Use [bold]arche track list[/bold] to see available tracks.")
        raise typer.Exit(1)

    if current_plan:
        slog(plan["id"], f"Switched from '{plan.get('name', '?')}'", "SWITCH")

    console.print(f"\n[green]✓ Switched to:[/green] [bold]{plan.get('name', plan['id'])}[/bold]")
    from core.status import show_resume
    show_resume()


@track_app.command("plan")
def track_plan(
    force: bool = typer.Option(False, "--force", help="Regenerate even if tasks already exist"),
) -> None:
    """Generate tasks from the active track's spec (runs the planner)."""
    _require_project()
    track = _require_active_track()
    track_id = track["id"]

    from agents.planner import generate_tasks
    from core.task_engine import load_tasks

    existing = load_tasks(track_id)
    if existing and not force:
        console.print(f"[yellow]{len(existing)} tasks already exist.[/yellow] Use [bold]--force[/bold] to regenerate.")
        raise typer.Exit(1)

    if force and existing:
        from core.task_engine import save_tasks
        save_tasks(track_id, [])
        console.print("[dim]Existing tasks cleared.[/dim]")

    generate_tasks(track_id, track)


@track_app.command("done")
def track_done() -> None:
    """Mark the active track as DONE."""
    _require_project()
    plan = _require_active_track()
    from core.track_manager import mark_track_done
    from core.session_logger import log as slog

    if not Confirm.ask(f"Mark track '{plan.get('name', plan['id'])}' as DONE?"):
        console.print("[dim]Aborted.[/dim]")
        return

    slog(plan["id"], f"Plan '{plan.get('name')}' marked as DONE", "DONE")
    mark_track_done(plan["id"])
    console.print(f"[green]✓ Track marked as DONE.[/green]")


# ── Task subcommands ─────────────────────────────────────────────────────────

@task_app.command("next")
def task_next() -> None:
    """Show the next pending task."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]

    from core.task_engine import start_task
    from core.status import show_current_task

    start_task(track_id)
    show_current_task(track_id)
    console.print("\n[dim]Ready? Run it with:[/dim] [bold]arche task run[/bold]")


@task_app.command("switch")
def task_switch(
    target: str = typer.Argument(..., help="Task number, id (or prefix), or title substring"),
) -> None:
    """Switch the current task (by number, id, or title)."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]

    from core.task_engine import switch_task, load_tasks, STATUS_DONE
    from core.status import TASK_STATUS_ICONS

    # Show numbered list first if target looks ambiguous (no digit-only, no id-like)
    tasks = load_tasks(track_id)
    if not tasks:
        console.print("[yellow]No tasks in this track.[/yellow]")
        raise typer.Exit(1)

    task = switch_task(track_id, target)

    if task is None:
        # Check if it matched a DONE task
        from core.task_engine import _resolve_task
        resolved = _resolve_task(tasks, target)
        if resolved and resolved["status"] == STATUS_DONE:
            console.print(f"[yellow]Task '{resolved['title']}' is already DONE and cannot be set as current.[/yellow]")
        else:
            console.print(f"[red]No task found matching:[/red] {target}")
            console.print("\nAvailable tasks:")
            for i, t in enumerate(tasks, 1):
                icon = TASK_STATUS_ICONS.get(t.get("status", "PENDING"), "·")
                console.print(f"  [dim]{i:>2}.[/dim] {icon} [{t['id']}] {t['title']}")
        raise typer.Exit(1)

    console.print(f"\n[green]✓ Current task:[/green] [bold]{task['title']}[/bold]")
    console.print(f"[dim]Run it with:[/dim] [bold]arche task run[/bold]")


@task_app.command("run")
def task_run(
    auto_done: bool = typer.Option(False, "--auto-done", help="Marque la tâche comme DONE automatiquement après"),
    comment: Optional[str] = typer.Option(None, "--comment", "-m", help="Commentaire ou contexte additionnel (bug constaté, précision…)"),
) -> None:
    """Lance la tâche courante : construit le contexte complet et appelle le LLM."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]

    from core.task_engine import get_current_task, start_task, complete_task
    from core.context import build_task_prompt, extract_archi_notes, append_archi
    from core.router import call_llm
    from core.session_logger import log as slog, log_task_done

    # S'assurer qu'une tâche est EN COURS
    task = get_current_task(track_id)
    if not task:
        console.print("[yellow]Aucune tâche en cours.[/yellow] Utilise [bold]arche task next[/bold] d'abord.")
        raise typer.Exit(1)

    start_task(track_id, task["id"])  # idempotent

    console.print(f"\n[bold cyan]arche task run[/bold cyan]")
    console.print(f"[dim]Tâche :[/dim] [bold]{task['title']}[/bold]")
    if comment:
        console.print(f"[dim]Commentaire :[/dim] {comment}")
    console.print(f"[dim]Contexte : spec + archi + tâches faites + session récente → {_model_label(plan)}[/dim]\n")

    # Construire le prompt avec tout le contexte
    prompt = build_task_prompt(track_id, plan, comment=comment or "")

    slog(track_id, f"Lancement tâche : **{task['title']}**" + (f"\n\nCommentaire : {comment}" if comment else ""), "RUN")

    # Appel LLM (phase dev par défaut, sauf si plan en mode debug/doc)
    phase = plan.get("phase", "dev")
    output = call_llm(prompt, phase=phase, track_meta=plan, stream=True)

    # Extraire et sauvegarder les notes d'architecture
    archi_notes = extract_archi_notes(output)
    if archi_notes:
        append_archi(track_id, archi_notes)
        console.print(f"\n[green]✓ Notes d'architecture sauvegardées dans archi.md[/green]")

    slog(track_id, f"Tâche exécutée : **{task['title']}**\n\nSortie LLM (extrait) :\n{output[:500]}…", "RUN")

    # Marquer comme done ?
    if auto_done:
        complete_task(track_id)
        log_task_done(track_id, task["title"])
        console.print(f"\n[green]✓ Tâche marquée DONE.[/green]")
        from core.task_engine import start_task as st
        next_task = st(track_id)
        if next_task:
            console.print(f"[cyan]→ Suivante :[/cyan] {next_task['title']}")
            console.print("[dim]Lance-la avec :[/dim] [bold]arche task run[/bold]")
        else:
            console.print("[green]Toutes les tâches sont complètes ![/green]")
    else:
        console.print(
            f"\n[dim]Une fois le travail fait :[/dim] [bold]arche task done[/bold]"
            f"  [dim]ou relance :[/dim] [bold]arche task run[/bold]"
        )


def _model_label(plan: dict) -> str:
    from core.router import get_model_for_phase
    phase = plan.get("phase", "dev")
    return get_model_for_phase(phase, plan)


@task_app.command("done")
def task_done(
    notes: str = typer.Option("", help="Optional notes for this task"),
) -> None:
    """Mark the current task as done and show the next one."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]

    from core.task_engine import complete_task, start_task, get_current_task
    from core.session_logger import log_task_done
    from core.status import show_current_task

    task = complete_task(track_id, notes=notes)
    if not task:
        console.print("[yellow]No task in progress.[/yellow]")
        return

    log_task_done(track_id, task["title"], notes)
    console.print(f"[green]✓ Completed:[/green] {task['title']}")

    # Start next
    next_task = start_task(track_id)
    if next_task:
        console.print(f"\n[cyan]→ Next:[/cyan] {next_task['title']}")
        if next_task.get("description"):
            console.print(f"   [dim]{next_task['description']}[/dim]")
    else:
        console.print("\n[green]All tasks completed![/green]")


@task_app.command("block")
def task_block(
    reason: str = typer.Argument(..., help="Reason why this task is blocked"),
) -> None:
    """Mark the current task as blocked."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]

    from core.task_engine import block_task
    from core.session_logger import log_task_blocked

    task = block_task(track_id, reason)
    if not task:
        console.print("[yellow]No task in progress.[/yellow]")
        return

    log_task_blocked(track_id, task["title"], reason)
    console.print(f"[red]✗ Blocked:[/red] {task['title']}")
    console.print(f"   Reason: {reason}")


@task_app.command("add")
def task_add(
    title: str = typer.Argument(..., help="Task title"),
    description: str = typer.Option("", help="Task description"),
) -> None:
    """Add a task manually to the active track."""
    _require_project()
    plan = _require_active_track()

    from core.task_engine import add_task, load_tasks
    from core.status import TASK_STATUS_ICONS
    task = add_task(plan["id"], title, description)
    all_tasks = load_tasks(plan["id"])
    num = next((i for i, t in enumerate(all_tasks, 1) if t["id"] == task["id"]), "?")
    icon = TASK_STATUS_ICONS.get(task["status"], "·")
    console.print(f"\n[green]✓ Task added:[/green]")
    console.print(f"  {icon} [dim]{task['id']}[/dim] {task['title']}  [dim](#{num})[/dim]")
    if task.get("description"):
        console.print(f"     [dim]{task['description']}[/dim]")


@task_app.command("help")
def task_help() -> None:
    """Show task command reference."""
    from rich.padding import Padding
    from rich.rule import Rule
    from rich.table import Table

    def cmd(text: str) -> str:
        return f"[bold yellow]{text}[/bold yellow]"

    console.print()
    console.print(Rule("[bold yellow]arche task[/bold yellow]  —  task management", style="yellow"))
    console.print()

    t = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    t.add_column("cmd",  style="bold yellow", no_wrap=True, min_width=38)
    t.add_column("desc", style="dim white")
    t.add_row("arche task run",                   "★ Run current task with full context → LLM")
    t.add_row("arche task run --auto-done",        "  Same + mark DONE automatically")
    t.add_row("arche task next",                   "  Pick next pending task (without running)")
    t.add_row("arche task switch <n|id|title>",    "  Jump to a specific task by number, id or title")
    t.add_row("arche task done [--notes \"…\"]",  "  Mark current task done, advance to next")
    t.add_row("arche task block \"<reason>\"",     "  Mark current task as blocked")
    t.add_row("arche task add \"<title>\"",        "  Add a task manually")
    t.add_row("arche task list",                   "  List all tasks in the active track")
    t.add_row("arche task show <n|id|title>",      "  Show full details of a task")
    t.add_row("arche task show <id> --edit",       "  Show + edit a task interactively")
    console.print(Padding(t, (0, 0, 1, 2)))
    console.print(Rule(style="dim"))
    console.print()


@task_app.command("list")
def task_list() -> None:
    """List all tasks in the active track."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]

    from core.task_engine import load_tasks
    from core.status import TASK_STATUS_ICONS
    tasks = load_tasks(track_id)

    if not tasks:
        console.print("[dim]No tasks yet.[/dim]")
        return

    console.print(f"\n[bold]Tasks for: {plan.get('name', track_id)}[/bold]\n")
    for i, t in enumerate(tasks, 1):
        status = t.get("status", "TODO")
        icon = TASK_STATUS_ICONS.get(status, "·")
        console.print(f"  {icon} [dim]{i:>2}.[/dim] [dim]{t['id']}[/dim]  {t['title']}")


@task_app.command("show")
def task_show(
    target: str = typer.Argument(..., help="Task number, id (or prefix), or title substring"),
    edit: bool = typer.Option(False, "--edit", help="Edit the task fields interactively"),
) -> None:
    """Show full details of a task, optionally edit it."""
    _require_project()
    plan = _require_active_track()
    track_id = plan["id"]

    from core.task_engine import load_tasks, update_task, _resolve_task
    from core.status import TASK_STATUS_ICONS
    from rich.rule import Rule

    tasks = load_tasks(track_id)
    task = _resolve_task(tasks, target)
    if not task:
        console.print(f"[red]No task found matching:[/red] {target}")
        raise typer.Exit(1)

    num = next((i for i, t in enumerate(tasks, 1) if t["id"] == task["id"]), "?")
    icon = TASK_STATUS_ICONS.get(task.get("status", "TODO"), "·")

    console.print()
    console.print(Rule(f"Task #{num}  [dim]{task['id']}[/dim]", style="yellow"))
    console.print(f"  {icon} [bold]{task['title']}[/bold]")
    console.print(f"  Status      [cyan]{task.get('status', 'TODO')}[/cyan]")
    if task.get("description"):
        console.print(f"  Description [dim]{task['description']}[/dim]")
    if task.get("notes"):
        console.print(f"  Notes       [yellow]{task['notes']}[/yellow]")
    if task.get("blocked_reason"):
        console.print(f"  Blocked     [red]{task['blocked_reason']}[/red]")
    if task.get("phase_id"):
        console.print(f"  Phase       [dim]{task['phase_id']}[/dim]")
    console.print(Rule(style="dim"))

    if edit:
        console.print("\n[dim]Press Enter to keep current value.[/dim]\n")
        new_title = Prompt.ask("  Title", default=task["title"])
        new_desc  = Prompt.ask("  Description", default=task.get("description", ""))
        new_notes = Prompt.ask("  Notes", default=task.get("notes", ""))

        updates = {}
        if new_title != task["title"]:
            updates["title"] = new_title
        if new_desc != task.get("description", ""):
            updates["description"] = new_desc
        if new_notes != task.get("notes", ""):
            updates["notes"] = new_notes

        if updates:
            update_task(track_id, task["id"], updates)
            console.print(f"\n[green]✓ Task updated.[/green]")
        else:
            console.print(f"\n[dim]No changes.[/dim]")


if __name__ == "__main__":
    app()
