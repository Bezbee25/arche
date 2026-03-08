"""Task queue management per plan."""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from core.track_manager import (
    TRACKS_DIR,
    get_current_track_id,
    load_yaml,
    save_yaml,
)

STATUS_TODO = "TODO"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_DONE = "DONE"
STATUS_BLOCKED = "BLOCKED"
# Legacy aliases — kept for backward-compat imports
STATUS_PENDING = "PENDING"
STATUS_SELECTED = "SELECTED"


def _tasks_path(track_id: str) -> Path:
    return TRACKS_DIR / track_id / "tasks.yaml"


def load_tasks(track_id: str, phase_id: Optional[str] = None) -> list[dict]:
    data = load_yaml(_tasks_path(track_id))
    tasks = data.get("tasks", [])
    for t in tasks:
        # Fix YAML integer IDs (all-numeric hex strings loaded as int by PyYAML)
        t["id"] = str(t.get("id", ""))
        # Migrate legacy statuses
        s = t.get("status")
        if s in (STATUS_PENDING, STATUS_SELECTED):
            t["status"] = STATUS_TODO
    if phase_id is not None:
        from core.track_manager import _DEFAULT_PHASE_ID
        if phase_id == _DEFAULT_PHASE_ID:
            tasks = [t for t in tasks if not t.get("phase_id") or t.get("phase_id") == _DEFAULT_PHASE_ID]
        else:
            tasks = [t for t in tasks if t.get("phase_id") == phase_id]
    return tasks


def save_tasks(track_id: str, tasks: list[dict]) -> None:
    save_yaml(_tasks_path(track_id), {"tasks": tasks})


def add_task(track_id: str, title: str, description: str = "", notes: str = "", phase_id: str = "") -> dict:
    tasks = load_tasks(track_id)
    task = {
        "id": uuid.uuid4().hex[:8],
        "title": title,
        "description": description,
        "notes": notes,
        "phase_id": phase_id,
        "status": STATUS_TODO,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    tasks.append(task)
    save_tasks(track_id, tasks)
    return task


def add_tasks_bulk(track_id: str, task_list: list[dict], phase_id: str = "") -> list[dict]:
    """Add multiple tasks at once. Each dict: 'title', optionally 'description', 'phase_id'."""
    tasks = load_tasks(track_id)
    new_tasks = []
    now = datetime.now().isoformat()
    for item in task_list:
        task = {
            "id": uuid.uuid4().hex[:8],
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "notes": item.get("notes", ""),
            "phase_id": item.get("phase_id", phase_id),
            "status": STATUS_TODO,
            "created_at": now,
            "updated_at": now,
        }
        tasks.append(task)
        new_tasks.append(task)
    save_tasks(track_id, tasks)
    return new_tasks


def get_current_task(track_id: str) -> Optional[dict]:
    """Return the IN_PROGRESS task, then SELECTED, then first TODO."""
    tasks = load_tasks(track_id)
    for status in (STATUS_IN_PROGRESS, STATUS_SELECTED, STATUS_TODO):
        for t in tasks:
            if t["status"] == status:
                return t
    return None


def get_next_task(track_id: str) -> Optional[dict]:
    """Return the first TODO task."""
    tasks = load_tasks(track_id)
    for t in tasks:
        if t["status"] == STATUS_TODO:
            return t
    return None


def start_task(track_id: str, task_id: Optional[str] = None) -> Optional[dict]:
    """Mark a task as IN_PROGRESS. If no task_id, picks first IN_PROGRESS then first TODO."""
    tasks = load_tasks(track_id)
    # If there's already an IN_PROGRESS task, return it
    for t in tasks:
        if t["status"] == STATUS_IN_PROGRESS:
            if not task_id or t["id"] == task_id:
                return t

    target = None
    if task_id:
        for t in tasks:
            if t["id"] == task_id:
                target = t
                break
    else:
        for t in tasks:
            if t["status"] == STATUS_TODO:
                target = t
                break

    if not target:
        return None

    target["status"] = STATUS_IN_PROGRESS
    target["updated_at"] = datetime.now().isoformat()
    save_tasks(track_id, tasks)
    return target


def complete_task(track_id: str, task_id: Optional[str] = None, notes: str = "") -> Optional[dict]:
    """Mark current IN_PROGRESS/SELECTED (or specified) task as DONE."""
    tasks = load_tasks(track_id)
    target = None
    for t in tasks:
        if task_id and t["id"] == task_id:
            target = t
            break
        if not task_id and t["status"] == STATUS_IN_PROGRESS:
            target = t
            break
    if not target and not task_id:
        for t in tasks:
            if t["status"] == STATUS_TODO:
                target = t
                break

    if not target:
        return None

    target["status"] = STATUS_DONE
    target["updated_at"] = datetime.now().isoformat()
    if notes:
        target["notes"] = (target.get("notes", "") + "\n" + notes).strip()
    save_tasks(track_id, tasks)
    return target


def block_task(track_id: str, reason: str, task_id: Optional[str] = None) -> Optional[dict]:
    """Mark current task as BLOCKED."""
    tasks = load_tasks(track_id)
    target = None
    for t in tasks:
        if task_id and t["id"] == task_id:
            target = t
            break
        if not task_id and t["status"] == STATUS_IN_PROGRESS:
            target = t
            break

    if not target:
        return None

    target["status"] = STATUS_BLOCKED
    target["updated_at"] = datetime.now().isoformat()
    target["blocked_reason"] = reason
    save_tasks(track_id, tasks)
    return target


def switch_task(track_id: str, target: str) -> Optional[dict]:
    """Set a task as IN_PROGRESS. Previous IN_PROGRESS → TODO. DONE tasks protected."""
    tasks = load_tasks(track_id)
    resolved = _resolve_task(tasks, target)
    if not resolved:
        return None
    if resolved["status"] == STATUS_DONE:
        return None

    now = datetime.now().isoformat()
    for t in tasks:
        if t["status"] == STATUS_IN_PROGRESS and t["id"] != resolved["id"]:
            t["status"] = STATUS_TODO
            t["updated_at"] = now

    resolved["status"] = STATUS_IN_PROGRESS
    resolved["updated_at"] = now
    save_tasks(track_id, tasks)
    return resolved


def select_task(track_id: str, task_id: str) -> Optional[dict]:
    """Alias: select a task by id (sets SELECTED status)."""
    return switch_task(track_id, task_id)


def _resolve_task(tasks: list[dict], target: str) -> Optional[dict]:
    """Resolve a task by id prefix, 1-based index, or title substring."""
    # 1-based numeric index
    if target.isdigit():
        idx = int(target) - 1
        if 0 <= idx < len(tasks):
            return tasks[idx]
    # Exact id
    for t in tasks:
        if t["id"] == target:
            return t
    # Id prefix
    for t in tasks:
        if t["id"].startswith(target):
            return t
    # Title substring (case-insensitive)
    target_lower = target.lower()
    for t in tasks:
        if target_lower in t.get("title", "").lower():
            return t
    return None


def update_task(track_id: str, task_id: str, updates: dict) -> Optional[dict]:
    """Update mutable fields of a task."""
    tasks = load_tasks(track_id)
    target = None
    for t in tasks:
        if t["id"] == task_id:
            target = t
            break
    if not target:
        return None
    for field in ("title", "description", "notes", "status", "type"):
        if field in updates and updates[field] is not None:
            target[field] = updates[field]
    target["updated_at"] = datetime.now().isoformat()
    save_tasks(track_id, tasks)
    return target


def delete_task(track_id: str, task_id: str) -> bool:
    """Remove a task by id. Returns True if found and deleted."""
    tasks = load_tasks(track_id)
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) == len(tasks):
        return False
    save_tasks(track_id, new_tasks)
    return True


def delete_tasks_for_phase(track_id: str, phase_id: str) -> int:
    """Remove all tasks belonging to a phase. Returns count deleted."""
    tasks = load_tasks(track_id)
    new_tasks = [t for t in tasks if t.get("phase_id") != phase_id]
    deleted = len(tasks) - len(new_tasks)
    save_tasks(track_id, new_tasks)
    return deleted


def get_task_stats(track_id: str, phase_id: Optional[str] = None) -> dict:
    tasks = load_tasks(track_id, phase_id)
    stats = {
        STATUS_TODO: 0,
        STATUS_IN_PROGRESS: 0,
        STATUS_DONE: 0,
        STATUS_BLOCKED: 0,
        "total": len(tasks),
    }
    for t in tasks:
        status = t.get("status", STATUS_TODO)
        if status in stats:
            stats[status] += 1
    return stats
