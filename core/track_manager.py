"""Track management: CRUD, switch active, état."""
from __future__ import annotations

import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

_MODELS_DEFAULT_YAML = Path(__file__).parent / "models_default.yaml"

STORAGE_DIR = Path(".arche-storage")
TRACKS_DIR = STORAGE_DIR / "tracks"
PROJECT_FILE = STORAGE_DIR / "project.yaml"
CURRENT_FILE = STORAGE_DIR / "current.yaml"

STATUS_ACTIVE = "ACTIVE"
STATUS_PAUSED = "PAUSED"
STATUS_DONE = "DONE"


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s/-]", "", text.lower())
    text = re.sub(r"[\s]+", "-", text.strip())
    return text[:64]


def _tracks_dir(track_id: str) -> Path:
    return TRACKS_DIR / track_id


def _meta_path(track_id: str) -> Path:
    return _tracks_dir(track_id) / "meta.yaml"


def _tasks_path(track_id: str) -> Path:
    return _tracks_dir(track_id) / "tasks.yaml"


def _spec_path(track_id: str) -> Path:
    return _tracks_dir(track_id) / "spec.md"


def _sessions_dir(track_id: str) -> Path:
    return _tracks_dir(track_id) / "sessions"


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def load_project() -> dict:
    return load_yaml(PROJECT_FILE)


def load_instructions() -> dict:
    """Load instructions manifest to ensure it exists and is ready."""
    try:
        from core.instruction_store import InstructionStore
        store = InstructionStore()
        manifest = store.load_manifest()
        # Try to use pydantic dict() method, fall back to dict() if it fails
        try:
            return manifest.dict() if manifest else {"instructions": [], "version": "1.0.0"}
        except AttributeError:
            # If manifest doesn't have dict() method, return as dict
            return dict(manifest) if manifest else {"instructions": [], "version": "1.0.0"}
    except ImportError:
        # If pydantic is not available, return empty manifest
        return {"instructions": [], "version": "1.0.0"}


def save_project(data: dict) -> None:
    save_yaml(PROJECT_FILE, data)
    # Load and persist instructions if they exist
    try:
        from core.instruction_store import InstructionStore
        store = InstructionStore()
        store.load_manifest()  # Ensure manifest is loaded
    except ImportError:
        # pydantic not available, skip instructions loading
        pass


_JIRA_DEFAULTS: dict = {"url": "", "login": "", "api_key": ""}


def load_jira_settings() -> dict:
    project = load_project()
    stored = project.get("jira", {}) or {}
    return {**_JIRA_DEFAULTS, **stored}


def save_jira_settings(url: str, login: str, api_key: str) -> None:
    project = load_project()
    project["jira"] = {"url": url.strip(), "login": login.strip(), "api_key": api_key.strip()}
    save_yaml(PROJECT_FILE, project)


def get_current_track_id() -> Optional[str]:
    data = load_yaml(CURRENT_FILE)
    return data.get("active_track_id")


def set_current_track_id(track_id: Optional[str]) -> None:
    save_yaml(CURRENT_FILE, {"active_track_id": track_id})


def list_tracks() -> list[dict]:
    if not TRACKS_DIR.exists():
        return []
    plans = []
    for d in sorted(TRACKS_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "meta.yaml"
        if meta_path.exists():
            meta = load_yaml(meta_path)
            if meta.get("id"):
                plans.append(meta)
    # Sort: ACTIVE first, then PAUSED, then DONE; within same status by created_at desc
    order = {STATUS_ACTIVE: 0, STATUS_PAUSED: 1, STATUS_DONE: 2}
    plans.sort(key=lambda p: (order.get(p.get("status", STATUS_PAUSED), 1), p.get("created_at", "")))
    return plans


def get_track(track_id: str) -> Optional[dict]:
    meta_path = _meta_path(track_id)
    if not meta_path.exists():
        # Try matching by slug prefix
        if TRACKS_DIR.exists():
            for d in TRACKS_DIR.iterdir():
                if d.name.startswith(track_id) or d.name == track_id:
                    mp = d / "meta.yaml"
                    if mp.exists():
                        return load_yaml(mp)
        return None
    return load_yaml(meta_path)


def get_active_track() -> Optional[dict]:
    track_id = get_current_track_id()
    if not track_id:
        return None
    return get_track(track_id)


def new_track(name: str, phase: str = "spec", track_type: str = "feature") -> dict:
    """Create a new plan and set it as active (pausing previous active)."""
    track_id = _slugify(name)
    # Ensure unique id
    if _tracks_dir(track_id).exists():
        track_id = f"{track_id}-{uuid.uuid4().hex[:6]}"

    now = datetime.now().isoformat()
    meta = {
        "id": track_id,
        "name": name,
        "status": STATUS_ACTIVE,
        "phase": phase,
        "track_type": track_type,
        "created_at": now,
        "updated_at": now,
    }

    # Pause currently active plan
    active_id = get_current_track_id()
    if active_id:
        _update_track_status(active_id, STATUS_PAUSED)

    plan_dir = _tracks_dir(track_id)
    plan_dir.mkdir(parents=True, exist_ok=True)
    _sessions_dir(track_id).mkdir(parents=True, exist_ok=True)
    save_yaml(_meta_path(track_id), meta)
    save_yaml(_tasks_path(track_id), {"tasks": []})

    # Write empty spec
    spec_path = _spec_path(track_id)
    if not spec_path.exists():
        spec_path.write_text(f"# Spec: {name}\n\n")

    # Copy model registry for per-track overrides
    models_dst = plan_dir / "models.yaml"
    if not models_dst.exists() and _MODELS_DEFAULT_YAML.exists():
        shutil.copy(_MODELS_DEFAULT_YAML, models_dst)

    set_current_track_id(track_id)
    return meta


def switch_track(track_id_or_name: str) -> Optional[dict]:
    """Switch active plan. Pauses current, activates target."""
    # Resolve plan
    target = _resolve_track(track_id_or_name)
    if not target:
        return None

    target_id = target["id"]

    # Pause current
    current_id = get_current_track_id()
    if current_id and current_id != target_id:
        _update_track_status(current_id, STATUS_PAUSED)

    # Activate target
    _update_track_status(target_id, STATUS_ACTIVE)
    set_current_track_id(target_id)
    return get_track(target_id)


def mark_track_done(track_id: Optional[str] = None) -> Optional[dict]:
    """Mark plan as DONE."""
    if not track_id:
        track_id = get_current_track_id()
    if not track_id:
        return None
    _update_track_status(track_id, STATUS_DONE)
    set_current_track_id(None)
    return get_track(track_id)


def update_track_phase(track_id: str, phase: str) -> None:
    meta = load_yaml(_meta_path(track_id))
    meta["phase"] = phase
    meta["updated_at"] = datetime.now().isoformat()
    save_yaml(_meta_path(track_id), meta)


def update_track_meta(track_id: str, **kwargs) -> None:
    meta = load_yaml(_meta_path(track_id))
    meta.update(kwargs)
    meta["updated_at"] = datetime.now().isoformat()
    save_yaml(_meta_path(track_id), meta)


def _update_track_status(track_id: str, status: str) -> None:
    meta_path = _meta_path(track_id)
    if not meta_path.exists():
        return
    meta = load_yaml(meta_path)
    meta["status"] = status
    meta["updated_at"] = datetime.now().isoformat()
    save_yaml(meta_path, meta)


def _resolve_track(id_or_name: str) -> Optional[dict]:
    """Resolve a plan by exact id, prefix, or name substring."""
    plans = list_tracks()
    # Exact match
    for p in plans:
        if p["id"] == id_or_name:
            return p
    # Prefix
    for p in plans:
        if p["id"].startswith(id_or_name):
            return p
    # Name substring
    id_or_name_lower = id_or_name.lower()
    for p in plans:
        if id_or_name_lower in p.get("name", "").lower():
            return p
    return None


def get_spec(track_id: str) -> str:
    path = _spec_path(track_id)
    return path.read_text() if path.exists() else ""


def save_spec(track_id: str, content: str) -> None:
    _spec_path(track_id).write_text(content)


def get_track_files(track_id: str) -> list:
    """Return the list of track-level attached files from meta.yaml."""
    meta = load_yaml(_meta_path(track_id))
    return meta.get("files", [])


def set_track_files(track_id: str, files: list) -> None:
    """Set the list of track-level attached files in meta.yaml."""
    meta = load_yaml(_meta_path(track_id))
    meta["files"] = files
    meta["updated_at"] = datetime.now().isoformat()
    save_yaml(_meta_path(track_id), meta)


# ── Phase management ─────────────────────────────────────────────────────────

_DEFAULT_PHASE_ID = "default"
_DEFAULT_PHASE = {"id": _DEFAULT_PHASE_ID, "name": "", "description": "", "depends_on": []}


def _phases_path(track_id: str) -> Path:
    return _tracks_dir(track_id) / "phases.yaml"


def load_phases(track_id: str) -> list[dict]:
    """Load phases. Returns [default phase] if none defined."""
    path = _phases_path(track_id)
    if not path.exists():
        return [dict(_DEFAULT_PHASE)]
    data = load_yaml(path)
    phases = data.get("phases", [])
    return phases if phases else [dict(_DEFAULT_PHASE)]


def save_phases(track_id: str, phases: list[dict]) -> None:
    save_yaml(_phases_path(track_id), {"phases": phases})


def add_phase(track_id: str, name: str, description: str = "", depends_on: Optional[list] = None) -> dict:
    phases = load_phases(track_id)
    # Replace the auto-created default phase when adding a real named phase
    if len(phases) == 1 and phases[0]["id"] == _DEFAULT_PHASE_ID and not phases[0]["name"]:
        phases = []
    phase = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "description": description,
        "depends_on": depends_on or [],
        "created_at": datetime.now().isoformat(),
    }
    phases.append(phase)
    save_phases(track_id, phases)
    return phase


def add_phases_bulk(track_id: str, phase_list: list[dict]) -> list[dict]:
    """Add multiple phases, replacing auto-default. Each dict: {name, description, depends_on}."""
    phases = load_phases(track_id)
    if len(phases) == 1 and phases[0]["id"] == _DEFAULT_PHASE_ID and not phases[0]["name"]:
        phases = []
    now = datetime.now().isoformat()
    new_phases = []
    for item in phase_list:
        phase = {
            "id": uuid.uuid4().hex[:8],
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "depends_on": item.get("depends_on", []),
            "created_at": now,
        }
        phases.append(phase)
        new_phases.append(phase)
    save_phases(track_id, phases)
    return new_phases


def get_phase(track_id: str, phase_id: str) -> Optional[dict]:
    return next((p for p in load_phases(track_id) if p["id"] == phase_id), None)


def update_phase(track_id: str, phase_id: str, updates: dict) -> Optional[dict]:
    phases = load_phases(track_id)
    target = next((p for p in phases if p["id"] == phase_id), None)
    if not target:
        return None
    for field in ("name", "description", "depends_on"):
        if field in updates and updates[field] is not None:
            target[field] = updates[field]
    save_phases(track_id, phases)
    return target


def delete_phase(track_id: str, phase_id: str) -> bool:
    phases = load_phases(track_id)
    new_phases = [p for p in phases if p["id"] != phase_id]
    if len(new_phases) == len(phases):
        return False
    if not new_phases:
        new_phases = [dict(_DEFAULT_PHASE)]
    save_phases(track_id, new_phases)
    # Also delete all tasks belonging to this phase
    from core.task_engine import delete_tasks_for_phase
    delete_tasks_for_phase(track_id, phase_id)
    return True
