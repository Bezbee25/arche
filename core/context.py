"""Build the rich context prompt to pass to the LLM for a task."""
from __future__ import annotations

from pathlib import Path

from core.track_manager import (
    TRACKS_DIR,
    get_spec,
    load_project,
    load_yaml,
)
from core.scanner import get_global_archi, get_global_memory, GLOBAL_MEMORY_PATH
from core.session_logger import get_session_log, list_sessions
from core.task_engine import STATUS_DONE, STATUS_IN_PROGRESS, STATUS_TODO, load_tasks


_MAX_INSTRUCTION_CHARS = 4000


def _sanitize_instruction_name(name: str) -> str:
    """Strip markdown/special chars from an instruction name for use in a heading."""
    name = name.strip().lstrip("#").strip()
    name = " ".join(name.split())
    return name or "Instruction"


def _parse_builtin_instruction(instruction_id: str, raw: str) -> tuple[str, str]:
    """Extract name and body from a built-in .md file.

    The first `# Heading` line is used as the name and removed from the body
    so it isn't duplicated when formatted as `### Name` in the prompt.
    """
    lines = raw.splitlines()
    name = instruction_id
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            name = line[2:].strip()
            body_start = i + 1
            break
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1
    content = "\n".join(lines[body_start:]).strip()
    return _sanitize_instruction_name(name), content


def _sanitize_instruction_content(content: str) -> str:
    """Downgrade headings in instruction content to avoid conflicts with the prompt
    structure, and truncate to a reasonable length."""
    if not content:
        return ""
    lines = []
    for line in content.splitlines():
        if line.startswith("## "):
            line = "####" + line[2:]
        elif line.startswith("# "):
            line = "###" + line[1:]
        lines.append(line)
    result = "\n".join(lines).strip()
    if len(result) > _MAX_INSTRUCTION_CHARS:
        result = result[:_MAX_INSTRUCTION_CHARS].rstrip() + "\n\n*(instruction truncated)*"
    return result


def _archi_path(track_id: str) -> Path:
    return TRACKS_DIR / track_id / "archi.md"


def get_archi(track_id: str) -> str:
    path = _archi_path(track_id)
    return path.read_text() if path.exists() else ""


def append_archi(track_id: str, notes: str) -> None:
    """Append notes to archi.md (creates the file if needed)."""
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    path = _archi_path(track_id)
    header = f"\n\n---\n*{now}*\n\n"
    with open(path, "a") as f:
        f.write(header + notes.strip() + "\n")
    # Propagate to global cross-track memory
    memory_header = f"\n\n---\n*{now}* | track: {track_id}\n\n"
    GLOBAL_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_MEMORY_PATH, "a") as f:
        f.write(memory_header + notes.strip() + "\n")


_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}


def _is_image_file(path: str) -> bool:
    return Path(path).suffix.lower() in _IMAGE_EXTENSIONS


def split_files_by_type(files: list[str]) -> tuple[list[str], list[str]]:
    """Split a list of file paths into (text_files, image_files)."""
    text_files = [f for f in files if not _is_image_file(f)]
    image_files = [f for f in files if _is_image_file(f)]
    return text_files, image_files


def build_task_prompt(track_id: str, track_meta: dict, comment: str = "", selected_instruction_ids: list = None, attached_files: list = None) -> str:
    """Build the full prompt to execute the current task."""
    project = load_project()
    tasks = load_tasks(track_id)
    spec = get_spec(track_id)
    global_archi = get_global_archi()
    global_memory = get_global_memory()
    archi = get_archi(track_id)

    # Load selected instructions if provided
    selected_instructions = []
    missing_instruction_ids = []
    if selected_instruction_ids:
        store = None
        try:
            from core.instruction_store import InstructionStore
            store = InstructionStore()
        except Exception:
            pass

        instructions_dir = Path(__file__).parent.parent / "instructions"
        local_instructions_dir = Path(".arche-storage/instructions")

        for instruction_id in selected_instruction_ids:
            loaded = False

            # 1. Try the user store (manifest.json) first
            if store is not None:
                try:
                    instruction = store.get_instruction(instruction_id)
                    if instruction and instruction.is_enabled:
                        selected_instructions.append({
                            "name": _sanitize_instruction_name(instruction.name),
                            "content": _sanitize_instruction_content(instruction.content),
                        })
                        loaded = True
                except Exception:
                    pass

            if loaded:
                continue

            # 2. Local project instructions: .arche-storage/instructions/*.md
            local_md = local_instructions_dir / f"{instruction_id}.md"
            if local_md.exists():
                try:
                    raw = local_md.read_text(encoding="utf-8")
                    name, content = _parse_builtin_instruction(instruction_id, raw)
                    selected_instructions.append({
                        "name": name,
                        "content": _sanitize_instruction_content(content),
                    })
                    loaded = True
                except Exception:
                    pass

            if loaded:
                continue

            # 3. Fallback: search built-in (global) instruction files
            if instructions_dir.exists():
                try:
                    for md_file in instructions_dir.rglob(f"{instruction_id}.md"):
                        raw = md_file.read_text(encoding="utf-8")
                        name, content = _parse_builtin_instruction(instruction_id, raw)
                        selected_instructions.append({
                            "name": name,
                            "content": _sanitize_instruction_content(content),
                        })
                        loaded = True
                        break
                except Exception:
                    pass

            if not loaded:
                missing_instruction_ids.append(instruction_id)

    # Current task
    current = next((t for t in tasks if t["status"] == STATUS_IN_PROGRESS), None)
    if not current:
        current = next((t for t in tasks if t["status"] == STATUS_TODO), None)

    # Completed and pending tasks
    done_tasks = [t for t in tasks if t["status"] == STATUS_DONE]
    pending_tasks = [t for t in tasks if t["status"] not in (STATUS_DONE, STATUS_IN_PROGRESS)]

    # Recent session log (today or yesterday)
    sessions = list_sessions(track_id)
    recent_log = ""
    if sessions:
        recent_log = get_session_log(track_id, sessions[0])[:1500]

    # ── Assemble the prompt ────────────────────────────────────────────────
    parts = []

    parts.append(
        f"You are a development agent working on the project **{project.get('name', track_id)}**.\n"
        f"Stack: {project.get('stack', 'not specified')}\n"
        f"Current track: **{track_meta.get('name', track_id)}**\n"
        f"Work in English."
    )

    protected_paths = project.get("protected_paths", [])
    if protected_paths:
        paths_list = "\n".join(f"  - {p}" for p in protected_paths)
        parts.append(
            f"## PROTECTED PATHS — READ ONLY\n\n"
            f"You may read these files/directories for context, "
            f"but you MUST NOT modify them (no Write, no Edit):\n\n"
            f"{paths_list}"
        )

    if spec and spec.strip():
        parts.append(f"## Track spec\n\n{spec}")

    if global_archi and global_archi.strip():
        parts.append(f"## Project architecture (global reference)\n\n{global_archi}")

    if global_memory and global_memory.strip():
        parts.append(f"## Shared memory (cross-track discoveries)\n\n{global_memory}")

    if archi and archi.strip():
        parts.append(f"## Track architecture notes\n\n{archi}")

    if done_tasks:
        done_parts = []
        for t in done_tasks:
            entry = f"✓ **{t['title']}**"
            if t.get("notes"):
                entry += f"\n   Findings: {t['notes']}"
            done_parts.append(entry)
        done_list = "\n\n".join(done_parts)
        parts.append(
            f"## Completed tasks\n\n"
            f"⚠ These tasks are DONE. Their findings are listed below — "
            f"do not redo them, use these results directly.\n\n"
            f"{done_list}"
        )

    if current:
        task_block = f"**{current['title']}**"
        if current.get("description"):
            task_block += f"\n\n{current['description']}"
        if current.get("notes"):
            task_block += f"\n\nExisting notes: {current['notes']}"
        parts.append(f"## Current task (to execute)\n\n{task_block}")

    if pending_tasks:
        pending_list = "\n".join(f"  · {t['title']}" for t in pending_tasks)
        parts.append(f"## Upcoming tasks (for context)\n\n{pending_list}")

    if recent_log:
        parts.append(f"## Recent session log\n\n{recent_log}")

    if comment and comment.strip():
        parts.append(f"## Developer comment\n\n{comment.strip()}")

    if selected_instructions:
        instructions_text = "\n\n".join(
            f"### {inst['name']}\n\n{inst['content']}"
            for inst in selected_instructions
        )
        warning = ""
        if missing_instruction_ids:
            ids_str = ", ".join(f"`{i}`" for i in missing_instruction_ids)
            warning = f"\n\n> ⚠ Instructions not found (ignored): {ids_str}"
        parts.append(f"## Selected instructions\n\n{instructions_text}{warning}")
    elif missing_instruction_ids:
        ids_str = ", ".join(f"`{i}`" for i in missing_instruction_ids)
        parts.append(
            f"## Selected instructions\n\n"
            f"> ⚠ Requested instructions not found (ignored): {ids_str}"
        )

    # Inject text file contents (images are handled separately via CLI flags)
    if attached_files:
        file_parts = []
        for file_path in attached_files:
            if _is_image_file(file_path):
                continue  # images passed via CLI flag, not embedded in prompt
            p = Path(file_path)
            if not p.exists():
                file_parts.append(f"> ⚠ File not found: {file_path}")
            else:
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    file_parts.append(f"### {file_path}\n{content}")
                except Exception:
                    file_parts.append(f"> ⚠ Cannot read: {file_path}")
        if file_parts:
            parts.append("## Attached files\n\n" + "\n\n".join(file_parts))

    parts.append(
        "---\n"
        "Execute the current task. Be concrete and actionable.\n\n"
        "**IMPORTANT**: If previous tasks have already performed an analysis or audit, "
        "their results are in the 'Completed tasks' and 'Track architecture notes' sections. "
        "Use this information directly — do not redo already completed analysis.\n\n"
        "At the end of your response, add a mandatory section:\n\n"
        "## Architecture notes\n"
        "*(For analysis/audit tasks: summarise all key findings, precise locations, bugs found.*\n"
        "*For implementation tasks: decisions made, patterns used, changes applied.*\n"
        "*Always include information useful for upcoming tasks.)*\n"
        "If nothing to note, write: `(none)`"
    )

    return "\n\n".join(parts)


def extract_archi_notes(llm_output: str) -> str | None:
    """Extract the '## Architecture notes' section from LLM output."""
    for marker in ("## Architecture notes", "## Notes d'architecture"):
        idx = llm_output.find(marker)
        if idx != -1:
            notes = llm_output[idx + len(marker):].strip()
            if notes and not notes.lower().startswith("(none") and not notes.lower().startswith("(aucune"):
                return notes
    return None
