"""Session journal per track."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.track_manager import TRACKS_DIR


def _sessions_dir(track_id: str) -> Path:
    return TRACKS_DIR / track_id / "sessions"


def _current_session_path(track_id: str) -> Path:
    sessions_dir = _sessions_dir(track_id)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return sessions_dir / f"{date_str}.md"


def log(track_id: str, message: str, level: str = "INFO") -> None:
    """Append a timestamped entry to today's session log."""
    path = _current_session_path(track_id)
    now = datetime.now().strftime("%H:%M:%S")

    if not path.exists():
        path.write_text(f"# Session {datetime.now().strftime('%Y-%m-%d')}\n\n")

    with open(path, "a") as f:
        f.write(f"**[{now}]** `{level}` {message}\n\n")


def log_task_start(track_id: str, task_title: str) -> None:
    log(track_id, f"Started task: **{task_title}**", "TASK")


def log_task_done(track_id: str, task_title: str, notes: str = "") -> None:
    msg = f"Completed task: **{task_title}**"
    if notes:
        msg += f"\n  > {notes}"
    log(track_id, msg, "DONE")


def log_task_blocked(track_id: str, task_title: str, reason: str) -> None:
    log(track_id, f"Blocked task: **{task_title}** — {reason}", "BLOCKED")


def log_track_switch(track_id: str, from_track: str, to_track: str) -> None:
    log(track_id, f"Switched from `{from_track}` → `{to_track}`", "SWITCH")


def log_llm_call(track_id: str, model: str, phase: str) -> None:
    log(track_id, f"LLM call: `{model}` for phase `{phase}`", "LLM")


def get_session_log(track_id: str, date: str | None = None) -> str:
    if date:
        path = _sessions_dir(track_id) / f"{date}.md"
    else:
        path = _current_session_path(track_id)
    return path.read_text() if path.exists() else ""


def list_sessions(track_id: str) -> list[str]:
    sessions_dir = _sessions_dir(track_id)
    if not sessions_dir.exists():
        return []
    return sorted([f.stem for f in sessions_dir.glob("*.md")], reverse=True)
