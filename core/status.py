"""Rich terminal display for arche status."""
from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from core.track_manager import (
    STATUS_ACTIVE,
    STATUS_DONE,
    STATUS_PAUSED,
    get_active_track,
    list_tracks,
    load_project,
)
from core.task_engine import (
    STATUS_BLOCKED,
    STATUS_DONE as TASK_DONE,
    STATUS_IN_PROGRESS,
    STATUS_TODO,
    get_current_task,
    get_task_stats,
    load_tasks,
)

console = Console()

STATUS_COLORS = {
    STATUS_ACTIVE: "green",
    STATUS_PAUSED: "yellow",
    STATUS_DONE: "dim",
}

TASK_STATUS_ICONS = {
    TASK_DONE: "[green]✓[/green]",
    STATUS_IN_PROGRESS: "[cyan]▶[/cyan]",
    STATUS_TODO: "[dim]·[/dim]",
    STATUS_BLOCKED: "[red]✗[/red]",
}

PHASE_COLORS = {
    "spec": "magenta",
    "plan": "blue",
    "dev": "cyan",
    "debug": "red",
    "doc": "yellow",
    "review": "green",
}


def _track_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "white")
    return f"[{color}]{status}[/{color}]"


def _progress_bar(done: int, total: int, width: int = 12) -> str:
    if total == 0:
        return "░" * width
    filled = min(int(done / total * width), width)
    return "█" * filled + "░" * (width - filled)


def show_track_list() -> None:
    plans = list_tracks()
    project = load_project()

    title = f"arche — {project.get('name', 'unknown project')}"
    table = Table(title=title, show_header=True, header_style="bold", expand=True)
    table.add_column("Status", width=8)
    table.add_column("Plan", no_wrap=True)
    table.add_column("Phase", width=8)
    table.add_column("Progress", width=20)
    table.add_column("Tasks", width=8, justify="right")

    if not plans:
        console.print("[dim]No tracks yet. Use 'arche track new <name>' to create one.[/dim]")
        return

    for p in plans:
        track_id = p["id"]
        stats = get_task_stats(track_id)
        done = stats[TASK_DONE]
        total = stats["total"]
        bar = _progress_bar(done, total)
        status = p.get("status", STATUS_PAUSED)
        color = STATUS_COLORS.get(status, "white")
        phase = p.get("phase", "spec")
        phase_color = PHASE_COLORS.get(phase, "white")

        name_text = Text(p.get("name", track_id))
        if status == STATUS_ACTIVE:
            name_text.stylize("bold")

        table.add_row(
            _track_badge(status),
            name_text,
            f"[{phase_color}]{phase}[/{phase_color}]",
            f"[cyan]{bar}[/cyan]",
            f"[dim]{done}/{total}[/dim]",
            style="" if status != STATUS_ACTIVE else "on grey11",
        )

    console.print(table)


def show_resume() -> None:
    """Show full status of the active plan."""
    plan = get_active_track()
    project = load_project()

    console.print(f"\n[bold]arche[/bold] — [dim]{project.get('name', 'unknown project')}[/dim]\n")

    if not plan:
        console.print("[yellow]No active track.[/yellow] Use [bold]arche track new <name>[/bold] to start.")
        show_plan_list()
        return

    track_id = plan["id"]
    stats = get_task_stats(track_id)
    done = stats[TASK_DONE]
    total = stats["total"]
    phase = plan.get("phase", "spec")
    phase_color = PHASE_COLORS.get(phase, "white")

    # Header
    bar = _progress_bar(done, total, width=20)
    console.print(
        Panel(
            f"[bold]{plan.get('name', track_id)}[/bold]  [{phase_color}]{phase.upper()}[/{phase_color}]\n"
            f"[cyan]{bar}[/cyan]  [dim]{done}/{total} tasks[/dim]",
            title=f"[green]● ACTIVE TRACK[/green]",
            border_style="green",
        )
    )

    # Tasks
    tasks = load_tasks(track_id)
    if tasks:
        console.print("\n[bold]TASKS[/bold]")
        for i, t in enumerate(tasks, 1):
            status = t.get("status", STATUS_TODO)
            icon = TASK_STATUS_ICONS.get(status, "·")
            title = t.get("title", "")
            tid = f"[dim]{t.get('id', '')}[/dim]"
            suffix = ""
            if status == STATUS_IN_PROGRESS:
                suffix = "  [cyan bold][IN PROGRESS][/cyan bold]"
            elif status == STATUS_BLOCKED:
                suffix = f"  [red][BLOCKED: {t.get('blocked_reason', '')}][/red]"
            elif status == TASK_DONE:
                title = f"[dim]{title}[/dim]"
            console.print(f"  {icon} {tid} {title}{suffix}")
    else:
        console.print("[dim]No tasks yet. Use 'arche track spec' to generate tasks.[/dim]")

    # Other plans
    all_plans = list_tracks()
    other_plans = [p for p in all_plans if p["id"] != track_id and p.get("status") != STATUS_DONE]
    if other_plans:
        console.print("\n[dim]Other tracks:[/dim]")
        for p in other_plans:
            s = get_task_stats(p["id"])
            console.print(
                f"  [dim]{_track_badge(p['status'])} {p.get('name', p['id'])} "
                f"({s[TASK_DONE]}/{s['total']})[/dim]"
            )


def show_current_task(track_id: str) -> None:
    task = get_current_task(track_id)
    if not task:
        console.print("[green]All tasks completed![/green]")
        return
    status = task.get("status", STATUS_TODO)
    icon = TASK_STATUS_ICONS.get(status, "·")
    console.print(f"\n{icon} [bold]{task['title']}[/bold]  [dim]{task.get('id', '')}[/dim]")
    if task.get("description"):
        console.print(f"   [dim]{task['description']}[/dim]")
    if task.get("notes"):
        console.print(f"   [yellow]Notes:[/yellow] {task['notes']}")
