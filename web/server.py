"""FastAPI web server for arche."""
from __future__ import annotations

import asyncio
import json
import shlex
import shutil
import sys
import uuid
from pathlib import Path
from typing import Optional

# Ensure arche root is in path when running via uvicorn
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from core.track_manager import (
    get_active_track,
    get_track,
    list_tracks,
    mark_track_done,
    new_track,
    switch_track,
    load_project,
    save_project,
    load_phases,
    save_phases,
    add_phase,
    add_phases_bulk,
    get_phase,
    update_phase,
    delete_phase,
    _DEFAULT_PHASE_ID,
)
from core.task_engine import (
    add_task,
    block_task,
    complete_task,
    get_task_stats,
    load_tasks,
    select_task,
    start_task,
    switch_task,
    update_task,
)
from core.session_logger import get_session_log, list_sessions, log
from web.ws_terminal import TerminalManager

STATIC_DIR = Path(__file__).parent / "static"


# ── Request models (module-level avoids annotation resolution issues) ────────
class NewPlanRequest(BaseModel):
    name: str
    track_type: str = "feature"

class SwitchPlanRequest(BaseModel):
    track_id: str

class SaveSpecRequest(BaseModel):
    content: str

class NewTaskRequest(BaseModel):
    title: str
    description: str = ""
    phase_id: str = ""

class CompleteTaskRequest(BaseModel):
    task_id: Optional[str] = None
    notes: Optional[str] = ""

class BlockTaskRequest(BaseModel):
    reason: str
    task_id: Optional[str] = None

class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None

class NewPhaseRequest(BaseModel):
    name: str
    description: str = ""
    depends_on: list[str] = []

class UpdatePhaseRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    depends_on: Optional[list[str]] = None

class InterviewRequest(BaseModel):
    description: str
    qa: list[dict] = []

class ReworkRequest(BaseModel):
    review_issues: str = ""

class BulkTaskRunRequest(BaseModel):
    task_ids: list[str]  # List of task IDs to execute in order
    comment: str = ""
    auto_done: bool = True

class TemplateGenerationRequest(BaseModel):
    description: str
    subtypes: list[str] = []


def _parse_claude_json_line(raw: str) -> str:
    """Parse one JSONL line from `claude --output-format stream-json`, return display text."""
    raw = raw.strip()
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return raw  # not JSON → pass through as plain text (e.g. error messages)

    t = obj.get("type", "")

    if t == "assistant":
        parts = []
        msg = obj.get("message", obj)
        for block in msg.get("content", []):
            if not isinstance(block, dict):
                continue
            bt = block.get("type", "")
            if bt == "text":
                parts.append(block.get("text", ""))
            elif bt == "tool_use":
                name = block.get("name", "tool")
                inp = block.get("input", {})
                if name == "Read":
                    parts.append(f"[Reading: {inp.get('file_path', inp.get('path', ''))}]\n")
                elif name == "Bash":
                    parts.append(f"[$ {inp.get('command', inp.get('cmd', ''))}]\n")
                elif name in ("Write", "Edit"):
                    parts.append(f"[{name}: {inp.get('file_path', inp.get('path', ''))}]\n")
                elif name == "Glob":
                    parts.append(f"[Glob: {inp.get('pattern', '')}]\n")
                elif name == "Grep":
                    parts.append(f"[Grep: {inp.get('pattern', '')}]\n")
                else:
                    parts.append(f"[{name}]\n")
        return "".join(parts)

    if t == "text" and "text" in obj:
        return obj["text"]

    if t == "result":
        if obj.get("is_error") or obj.get("subtype") == "error":
            return f"\n⚠ Error: {obj.get('result', '')}\n"
        return ""  # final accumulated text — skip to avoid duplication

    return ""  # user (tool results), system events → skip


def _compute_phase_status(track_id: str, phase_id: str, all_phases: list[dict], _visited: frozenset = frozenset()) -> str:
    """Compute phase status: LOCKED, TODO, IN_PROGRESS, or DONE."""
    if phase_id in _visited:
        return "TODO"  # circular dep guard
    phase = next((p for p in all_phases if p["id"] == phase_id), None)
    if not phase:
        return "TODO"
    for dep_id in phase.get("depends_on", []):
        dep_status = _compute_phase_status(track_id, dep_id, all_phases, _visited | {phase_id})
        if dep_status != "DONE":
            return "LOCKED"
    tasks = load_tasks(track_id, phase_id)
    if not tasks:
        return "TODO"
    statuses = [t.get("status", "TODO") for t in tasks]
    if all(s == "DONE" for s in statuses):
        return "DONE"
    if any(s == "IN_PROGRESS" for s in statuses):
        return "IN_PROGRESS"
    return "TODO"


def _build_phases_detail(track_id: str) -> list[dict]:
    """Return phases with computed status, stats, and tasks."""
    phases = load_phases(track_id)
    result = []
    for ph in phases:
        phase_id = ph["id"]
        tasks = load_tasks(track_id, phase_id)
        stats = get_task_stats(track_id, phase_id)
        status = _compute_phase_status(track_id, phase_id, phases)
        result.append({**ph, "status": status, "stats": stats, "tasks": tasks})
    return result


# Token → init_cmd mapping for interactive terminal sessions
_pending_terminal_inits: dict[str, str] = {}


def create_app() -> FastAPI:
    app = FastAPI(title="arche", docs_url="/api/docs")

    terminal_manager = TerminalManager()

    # ── REST API ────────────────────────────────────────────────────────────

    @app.get("/api/project")
    def get_project():
        return load_project()

    @app.get("/api/settings/protected-paths")
    def get_protected_paths():
        project = load_project()
        return {"protected_paths": project.get("protected_paths", [])}

    @app.post("/api/settings/protected-paths")
    def save_protected_paths(req: dict):
        paths = req.get("protected_paths", [])
        project = load_project()
        project["protected_paths"] = [p.strip() for p in paths if p.strip()]
        save_project(project)
        return {"protected_paths": project["protected_paths"]}

    @app.get("/api/settings/theme")
    def get_theme():
        project = load_project()
        return {"theme": project.get("ui_theme", "dark")}

    @app.post("/api/settings/theme")
    def save_theme(req: dict):
        theme = req.get("theme", "dark")
        project = load_project()
        project["ui_theme"] = theme
        save_project(project)
        return {"theme": theme}

    @app.get("/api/tracks")
    def get_plans():
        plans = list_tracks()
        result = []
        for p in plans:
            stats = get_task_stats(p["id"])
            result.append({**p, "stats": stats})
        return result

    @app.get("/api/tracks/active")
    def get_active():
        plan = get_active_track()
        if not plan:
            return {"active": None}
        stats = get_task_stats(plan["id"])
        tasks = load_tasks(plan["id"])
        return {**plan, "stats": stats, "tasks": tasks}

    @app.get("/api/tracks/{track_id}")
    def get_plan_detail(track_id: str):
        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        stats = get_task_stats(track_id)
        tasks = load_tasks(track_id)
        sessions = list_sessions(track_id)
        phases = _build_phases_detail(track_id)
        return {**plan, "stats": stats, "tasks": tasks, "sessions": sessions, "phases": phases}

    @app.get("/api/tracks/{track_id}/spec")
    def get_plan_spec(track_id: str):
        from core.track_manager import get_spec
        content = get_spec(track_id)
        return {"content": content}

    # ── Phases ───────────────────────────────────────────────────────────

    @app.get("/api/tracks/{track_id}/phases")
    def get_plan_phases(track_id: str):
        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return _build_phases_detail(track_id)

    @app.post("/api/tracks/{track_id}/phases")
    def create_phase(track_id: str, req: NewPhaseRequest):
        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        phase = add_phase(track_id, req.name, req.description, req.depends_on)
        return phase

    @app.patch("/api/tracks/{track_id}/phases/{phase_id}")
    def patch_phase(track_id: str, phase_id: str, req: UpdatePhaseRequest):
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        phase = update_phase(track_id, phase_id, updates)
        if phase is None:
            raise HTTPException(status_code=404, detail="Phase not found")
        return phase

    @app.delete("/api/tracks/{track_id}/phases/{phase_id}")
    def remove_phase(track_id: str, phase_id: str):
        ok = delete_phase(track_id, phase_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Phase not found")
        return {"ok": True}

    @app.get("/api/tracks/{track_id}/phases/generate")
    async def stream_phase_generation(track_id: str):
        """Stream phase generation (LLM) from spec via SSE."""
        from agents.planner import PHASE_PLANNER_PROMPT, _parse_phase_list
        from core.track_manager import get_spec
        from core.router import _build_command, _get_cli_for_model, get_model_for_phase, get_tools_for_phase

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        spec = get_spec(track_id)
        if not spec or not spec.strip():
            raise HTTPException(status_code=400, detail="No spec found — save a spec first")

        prompt = PHASE_PLANNER_PROMPT.format(spec=spec)
        model = get_model_for_phase("plan", plan)
        cli = _get_cli_for_model(model)
        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")
        tools = get_tools_for_phase("plan", plan)
        cmd = _build_command(cli, model, None, tools)
        if cli == "claude":
            cmd += ["--output-format", "stream-json", "--verbose"]

        async def generate_phases():
            output_lines: list[str] = []
            yield f"data: __META__ {model} | phases\n\n"
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    limit=10 * 1024 * 1024,  # 10 MB — Claude JSON lines can be large
                )
                proc.stdin.write(prompt.encode())
                await proc.stdin.drain()
                proc.stdin.close()
                while True:
                    if cli == "claude":
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        raw = line.decode("utf-8", errors="replace")
                        text = _parse_claude_json_line(raw)
                        if text:
                            output_lines.append(text)
                            sse_lines = text.split("\n")
                            sse = "\n".join(f"data: {l}" for l in sse_lines)
                            yield f"{sse}\n\n"
                    else:
                        chunk = await proc.stdout.read(4096)
                        if not chunk:
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        output_lines.append(text)
                        lines = text.split("\n")
                        sse = "\n".join(f"data: {l}" for l in lines)
                        yield f"{sse}\n\n"
                await proc.wait()

                output_str = "".join(output_lines)
                phase_dicts = _parse_phase_list(output_str)
                if phase_dicts:
                    # Create phases, resolving depends_on indices to IDs
                    index_to_id: dict[str, str] = {}
                    created = []
                    for i, item in enumerate(phase_dicts):
                        dep_ids = [index_to_id[d] for d in item.get("depends_on_indices", []) if d in index_to_id]
                        phase = add_phase(track_id, item["name"], item["description"], dep_ids)
                        index_to_id[str(i + 1)] = phase["id"]
                        created.append(phase)
                    log(track_id, f"Generated {len(created)} phases via web UI", "PLANNER")
                    yield f"data: ✓ {len(created)} phases created.\n\n"
                else:
                    yield "data: ⚠ Could not parse phases from output.\n\n"
            except Exception as e:
                yield f"data: ⚠ Error: {e}\n\n"
            finally:
                yield "data: __DONE__\n\n"

        return StreamingResponse(
            generate_phases(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/tracks/{track_id}/phases/{phase_id}/tasks/generate")
    async def stream_phase_task_generation(track_id: str, phase_id: str):
        """Stream task generation for a specific phase via SSE."""
        from agents.planner import PHASE_TASK_PLANNER_PROMPT, _parse_task_list
        from core.track_manager import get_spec
        from core.router import _build_command, _get_cli_for_model, get_model_for_phase, get_tools_for_phase

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        phase = get_phase(track_id, phase_id)
        if not phase:
            raise HTTPException(status_code=404, detail="Phase not found")
        spec = get_spec(track_id)
        if not spec or not spec.strip():
            raise HTTPException(status_code=400, detail="No spec found")

        prompt = PHASE_TASK_PLANNER_PROMPT.format(
            spec=spec,
            phase_name=phase.get("name", ""),
            phase_description=phase.get("description", ""),
        )
        model = get_model_for_phase("plan", plan)
        cli = _get_cli_for_model(model)
        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")
        tools = get_tools_for_phase("plan", plan)
        cmd = _build_command(cli, model, None, tools)
        if cli == "claude":
            cmd += ["--output-format", "stream-json", "--verbose"]

        async def generate_phase_tasks():
            output_lines: list[str] = []
            yield f"data: __META__ {model} | plan\n\n"
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    limit=10 * 1024 * 1024,  # 10 MB — Claude JSON lines can be large
                )
                proc.stdin.write(prompt.encode())
                await proc.stdin.drain()
                proc.stdin.close()
                while True:
                    if cli == "claude":
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        raw = line.decode("utf-8", errors="replace")
                        text = _parse_claude_json_line(raw)
                        if text:
                            output_lines.append(text)
                            sse_lines = text.split("\n")
                            sse = "\n".join(f"data: {l}" for l in sse_lines)
                            yield f"{sse}\n\n"
                    else:
                        chunk = await proc.stdout.read(4096)
                        if not chunk:
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        output_lines.append(text)
                        lines = text.split("\n")
                        sse = "\n".join(f"data: {l}" for l in lines)
                        yield f"{sse}\n\n"
                await proc.wait()

                output_str = "".join(output_lines)
                tasks = _parse_task_list(output_str)
                if tasks:
                    from core.task_engine import add_tasks_bulk
                    add_tasks_bulk(track_id, tasks, phase_id=phase_id)
                    log(track_id, f"Generated {len(tasks)} tasks for phase '{phase.get('name', '')}' via web UI", "PLANNER")
                    yield f"data: ✓ {len(tasks)} tasks created.\n\n"
                else:
                    yield "data: ⚠ Could not parse tasks from output.\n\n"
            except Exception as e:
                yield f"data: ⚠ Error: {e}\n\n"
            finally:
                yield "data: __DONE__\n\n"

        return StreamingResponse(
            generate_phase_tasks(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/tracks/{track_id}/spec")
    def save_plan_spec(track_id: str, req: SaveSpecRequest):
        from core.track_manager import save_spec, update_track_phase
        save_spec(track_id, req.content)
        update_track_phase(track_id, "plan")
        return {"ok": True}

    @app.get("/api/tracks/{track_id}/spec/refine")
    async def stream_spec_refine(track_id: str):
        """Rewrite the plan spec with LLM then save it (SSE)."""
        from agents.analyst import REFINE_PROMPT
        from core.track_manager import get_spec, save_spec, update_track_phase
        from core.router import _build_command, _get_cli_for_model, get_model_for_phase

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        spec = get_spec(track_id)
        if not spec or not spec.strip():
            raise HTTPException(status_code=400, detail="No spec — save a spec first")

        prompt = REFINE_PROMPT.format(spec=spec)
        model = get_model_for_phase("spec", plan)
        cli = _get_cli_for_model(model)

        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")

        cmd = _build_command(cli, model, None, ["Read"])
        if cli == "claude":
            cmd += ["--output-format", "stream-json", "--verbose"]

        async def generate():
            chunks: list[str] = []
            yield f"data: __META__ {model} | spec\n\n"
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    limit=10 * 1024 * 1024,  # 10 MB — Claude JSON lines can be large
                )
                proc.stdin.write(prompt.encode())
                await proc.stdin.drain()
                proc.stdin.close()

                while True:
                    if cli == "claude":
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        raw = line.decode("utf-8", errors="replace")
                        text = _parse_claude_json_line(raw)
                        if text:
                            chunks.append(text)
                            sse_lines = text.split("\n")
                            sse = "\n".join(f"data: {l}" for l in sse_lines)
                            yield f"{sse}\n\n"
                    else:
                        chunk = await proc.stdout.read(4096)
                        if not chunk:
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        chunks.append(text)
                        lines = text.split("\n")
                        sse = "\n".join(f"data: {l}" for l in lines)
                        yield f"{sse}\n\n"

                await proc.wait()

                refined = "".join(chunks).strip()
                if refined:
                    save_spec(track_id, refined)
                    update_track_phase(track_id, "plan")
                    log(track_id, "Spec refined via web UI", "ANALYST")
            except Exception as e:
                yield f"data: ⚠ Error: {e}\n\n"
            finally:
                yield "data: __DONE__\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/tracks/{track_id}/tasks/generate")
    async def stream_task_generation(track_id: str):
        """Stream task generation (planner LLM) from the plan's spec via SSE."""
        from agents.planner import PLANNER_PROMPT, _parse_task_list
        from core.track_manager import get_spec, update_track_phase
        from core.router import (
            _build_command,
            _get_cli_for_model,
            get_model_for_phase,
            get_tools_for_phase,
        )

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        spec = get_spec(track_id)
        if not spec or not spec.strip():
            raise HTTPException(status_code=400, detail="No spec found — save a spec first")

        prompt = PLANNER_PROMPT.format(spec=spec)
        model = get_model_for_phase("plan", plan)
        cli = _get_cli_for_model(model)

        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")

        tools = get_tools_for_phase("plan", plan)
        cmd = _build_command(cli, model, None, tools)
        if cli == "claude":
            cmd += ["--output-format", "stream-json", "--verbose"]

        async def generate():
            output_lines: list[str] = []
            yield f"data: __META__ {model} | plan\n\n"
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    limit=10 * 1024 * 1024,  # 10 MB — Claude JSON lines can be large
                )
                proc.stdin.write(prompt.encode())
                await proc.stdin.drain()
                proc.stdin.close()

                line_count = 0
                while True:
                    if cli == "claude":
                        line = await proc.stdout.readline()
                        if not line:
                            print(f"[stream_task_run] EOF reached after {line_count} lines")
                            break
                        raw = line.decode("utf-8", errors="replace")
                        text = _parse_claude_json_line(raw)
                        if text:
                            line_count += 1
                            output_lines.append(text)
                            sse_lines = text.split("\n")
                            sse = "\n".join(f"data: {l}" for l in sse_lines)
                            yield f"{sse}\n\n"
                        else:
                            print(f"[stream_task_run] Skipped unparseable line: {raw[:50]}")
                    else:
                        chunk = await proc.stdout.read(4096)
                        if not chunk:
                            print(f"[stream_task_run] EOF reached (read mode)")
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        output_lines.append(text)
                        lines = text.split("\n")
                        sse = "\n".join(f"data: {l}" for l in lines)
                        yield f"{sse}\n\n"

                print(f"[stream_task_run] Process ended, waiting for exit...")
                await proc.wait()
                print(f"[stream_task_run] Process exited with code {proc.returncode}")

                output_str = "".join(output_lines)
                tasks = _parse_task_list(output_str)
                if tasks:
                    from core.session_logger import log as slog
                    from core.task_engine import add_tasks_bulk
                    add_tasks_bulk(track_id, tasks)
                    update_track_phase(track_id, "dev")
                    slog(track_id, f"Generated {len(tasks)} tasks via web UI planner", "PLANNER")
                    yield f"data: ✓ {len(tasks)} tasks created.\n\n"
                else:
                    yield "data: ⚠ Could not parse tasks from output.\n\n"
            except Exception as e:
                yield f"data: ⚠ Error: {e}\n\n"
            finally:
                yield "data: __DONE__\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/tracks/{track_id}/sessions/{session_date}")
    def get_plan_session(track_id: str, session_date: str):
        content = get_session_log(track_id, session_date)
        return {"content": content}

    @app.post("/api/tracks")
    def create_plan(req: NewPlanRequest):
        plan = new_track(req.name, track_type=req.track_type)
        log(plan["id"], f"Plan '{req.name}' created via web UI", "INIT")
        return plan

    @app.post("/api/tracks/switch")
    def switch_active_plan(req: SwitchPlanRequest):
        plan = switch_track(req.track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan

    @app.post("/api/tracks/{track_id}/done")
    def complete_plan(track_id: str):
        plan = mark_track_done(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan

    @app.get("/api/tracks/{track_id}/tasks")
    def get_plan_tasks(track_id: str):
        return load_tasks(track_id)

    @app.post("/api/tracks/{track_id}/tasks")
    def create_task(track_id: str, req: NewTaskRequest):
        task = add_task(track_id, req.title, req.description, phase_id=req.phase_id)
        return task

    @app.delete("/api/tracks/{track_id}/tasks/{task_id}")
    def remove_task(track_id: str, task_id: str):
        from core.task_engine import delete_task
        ok = delete_task(track_id, task_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"deleted": task_id}

    @app.post("/api/tracks/{track_id}/tasks/generate-template")
    def generate_tasks_template(track_id: str, req: TemplateGenerationRequest):
        from agents.planner import generate_tasks_from_template
        track = get_track(track_id)
        if not track:
            raise HTTPException(status_code=404, detail="Track not found")
        tasks = generate_tasks_from_template(track_id, track, req.description, req.subtypes)
        return {"tasks": tasks, "count": len(tasks)}

    @app.post("/api/tracks/{track_id}/tasks/next")
    def advance_task(track_id: str):
        task = start_task(track_id)
        return task or {"message": "No pending tasks"}

    @app.post("/api/tracks/{track_id}/tasks/done")
    def done_task(track_id: str, req: CompleteTaskRequest):
        task = complete_task(track_id, req.task_id, req.notes or "")
        return task or {"message": "No task in progress"}

    @app.post("/api/tracks/{track_id}/tasks/block")
    def block_plan_task(track_id: str, req: BlockTaskRequest):
        task = block_task(track_id, req.reason, req.task_id)
        return task or {"message": "No task in progress"}

    @app.post("/api/tracks/{track_id}/tasks/{task_id}/switch")
    def switch_plan_task(track_id: str, task_id: str):
        task = switch_task(track_id, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found or already DONE")
        return task

    @app.post("/api/tracks/{track_id}/tasks/{task_id}/select")
    def select_plan_task(track_id: str, task_id: str):
        task = select_task(track_id, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found or already DONE")
        return task

    @app.patch("/api/tracks/{track_id}/tasks/{task_id}")
    def patch_task(track_id: str, task_id: str, req: UpdateTaskRequest):
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        task = update_task(track_id, task_id, updates)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @app.get("/api/tracks/{track_id}/tasks/{task_id}/run")
    async def stream_task_run(track_id: str, task_id: str, comment: str = "", auto_done: bool = True):
        """Switch to task then stream LLM output via SSE."""
        from core.context import build_task_prompt, extract_archi_notes, append_archi
        from core.router import (
            _build_command,
            _get_cli_for_model,
            get_model_for_phase,
            get_tools_for_phase,
        )

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        switch_task(track_id, task_id)
        start_task(track_id)

        phase = plan.get("phase", "dev")
        model = get_model_for_phase(phase, plan)
        cli = _get_cli_for_model(model)

        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")

        tools = get_tools_for_phase(phase, plan)
        cmd = _build_command(cli, model, None, tools)
        if cli == "claude":
            cmd += ["--output-format", "stream-json", "--verbose"]
        prompt = build_task_prompt(track_id, plan, comment=comment)

        async def generate():
            output_lines: list[str] = []
            print(f"[stream_task_run] Starting stream for task {task_id}, cli={cli}, model={model}")
            yield f"data: __META__ {model} | {phase}\n\n"
            try:
                print(f"[stream_task_run] Creating subprocess: {' '.join(cmd[:3])}...")
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,  # merge stderr → no deadlock
                    limit=10 * 1024 * 1024,  # 10 MB — Claude JSON lines can be large
                )
                print(f"[stream_task_run] Subprocess created, writing {len(prompt)} bytes to stdin")
                proc.stdin.write(prompt.encode())
                await proc.stdin.drain()  # flush buffer to the pipe
                proc.stdin.close()
                print("[stream_task_run] Starting to read from subprocess output...")

                line_count = 0
                while True:
                    if cli == "claude":
                        line = await proc.stdout.readline()
                        if not line:
                            print(f"[stream_task_run] EOF reached after {line_count} lines")
                            break
                        raw = line.decode("utf-8", errors="replace")
                        text = _parse_claude_json_line(raw)
                        if text:
                            line_count += 1
                            output_lines.append(text)
                            sse_lines = text.split("\n")
                            sse = "\n".join(f"data: {l}" for l in sse_lines)
                            yield f"{sse}\n\n"
                        else:
                            print(f"[stream_task_run] Skipped unparseable line: {raw[:50]}")
                    else:
                        chunk = await proc.stdout.read(4096)
                        if not chunk:
                            print(f"[stream_task_run] EOF reached (read mode)")
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        output_lines.append(text)
                        lines = text.split("\n")
                        sse = "\n".join(f"data: {l}" for l in lines)
                        yield f"{sse}\n\n"

                print(f"[stream_task_run] Process ended, waiting for exit...")
                await proc.wait()
                print(f"[stream_task_run] Process exited with code {proc.returncode}")

                if not output_lines:
                    yield f"data: ⚠ Subprocess exited with no output (code {proc.returncode})\n\n"
                elif proc.returncode != 0:
                    yield f"data: ⚠ Subprocess exited with code {proc.returncode}\n\n"

                output_str = "".join(output_lines)
                notes = extract_archi_notes(output_str)
                if notes:
                    append_archi(track_id, notes)
                
                # Auto-done functionality
                if auto_done:
                    from core.task_engine import complete_task
                    complete_task(track_id, task_id, "Auto-completed after successful run")
            except Exception as e:
                print(f"[stream_task_run] Exception: {e}")
                import traceback
                traceback.print_exc()
                yield f"data: ⚠ Error: {e}\n\n"
            finally:
                yield "data: __DONE__\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/tracks/{track_id}/tasks/{task_id}/prepare-run")
    async def prepare_task_run(
        track_id: str, task_id: str, comment: str = "", auto_done: bool = True
    ):
        """Prepare a task for interactive PTY execution.

        Switches to the task, saves the prompt to a temp file, and returns
        a one-time token that the /ws/terminal WebSocket will use to inject
        the command into a real PTY shell.
        """
        from core.context import build_task_prompt
        from core.router import (
            _build_command,
            _get_cli_for_model,
            get_model_for_phase,
            get_tools_for_phase,
        )

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        switch_task(track_id, task_id)
        start_task(track_id)

        # Task type overrides track phase for LLM selection (dev/debug/doc)
        task_obj = next((t for t in load_tasks(track_id) if t.get("id") == task_id), {})
        phase = task_obj.get("type") or plan.get("phase", "dev")
        model = get_model_for_phase(phase, plan)
        cli = _get_cli_for_model(model)

        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")

        tools = get_tools_for_phase(phase, plan)
        cmd = _build_command(cli, model, None, tools)
        prompt = build_task_prompt(track_id, plan, comment=comment)

        # Use storage/tracks/{track_id}/tmp/ to stay within the project directory
        from core.track_manager import TRACKS_DIR
        tmp_dir = TRACKS_DIR / track_id / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = tmp_dir / f"prompt-{task_id[:8]}-{uuid.uuid4().hex[:8]}.txt"
        prompt_file.write_text(prompt, encoding="utf-8")

        script_file = tmp_dir / f"run-{uuid.uuid4().hex[:8]}.sh"
        auto_done_line = "[ $_EXIT -eq 0 ] && arche task done 2>/dev/null && echo '\\n✓ Task marked as done.'" if auto_done else ""
        script_file.write_text(
            "#!/bin/bash\n"
            f"{' '.join(shlex.quote(c) for c in cmd)} < {shlex.quote(str(prompt_file))}\n"
            "_EXIT=$?\n"
            f"rm -f {shlex.quote(str(prompt_file))}\n"
            f"rm -f {shlex.quote(str(script_file))}\n"
            f"{auto_done_line}\n",
            encoding="utf-8",
        )

        init_cmd = f"bash {shlex.quote(str(script_file))}"

        token = str(uuid.uuid4())
        _pending_terminal_inits[token] = init_cmd

        return {"token": token, "task_title": task_obj.get("title", "")}

    @app.post("/api/tracks/{track_id}/tasks/bulk-run")
    async def bulk_run_tasks(track_id: str, req: BulkTaskRunRequest):
        """Execute multiple tasks in sequence via streaming (one per task)."""
        from core.context import build_task_prompt, extract_archi_notes, append_archi
        from core.router import (
            _build_command,
            _get_cli_for_model,
            get_model_for_phase,
            get_tools_for_phase,
        )

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Track not found")

        if not req.task_ids:
            raise HTTPException(status_code=400, detail="No task IDs provided")

        # Validate all tasks exist and filter DONE ones
        all_tasks = load_tasks(track_id)
        task_map = {t["id"]: t for t in all_tasks}
        valid_task_ids = []
        for tid in req.task_ids:
            if tid not in task_map:
                raise HTTPException(status_code=404, detail=f"Task {tid} not found")
            task = task_map[tid]
            if task["status"] != "DONE":
                valid_task_ids.append(tid)

        if not valid_task_ids:
            raise HTTPException(status_code=400, detail="All tasks are already DONE")

        phase = plan.get("phase", "dev")
        model = get_model_for_phase(phase, plan)
        cli = _get_cli_for_model(model)

        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")

        tools = get_tools_for_phase(phase, plan)
        cmd_base = _build_command(cli, model, None, tools)
        if cli == "claude":
            cmd_base += ["--output-format", "stream-json", "--verbose"]

        async def generate_bulk():
            for task_num, task_id in enumerate(valid_task_ids, 1):
                # Update current task
                switch_task(track_id, task_id)
                start_task(track_id, task_id)

                task = task_map[task_id]
                prompt = build_task_prompt(track_id, plan, comment=req.comment)

                yield f"data: __TASK_START__ {task_num}/{len(valid_task_ids)} {task['title']}\n\n"

                output_lines: list[str] = []
                try:
                    proc = await asyncio.create_subprocess_exec(
                        *cmd_base,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        limit=10 * 1024 * 1024,
                    )
                    proc.stdin.write(prompt.encode())
                    await proc.stdin.drain()
                    proc.stdin.close()

                    while True:
                        if cli == "claude":
                            line = await proc.stdout.readline()
                            if not line:
                                break
                            raw = line.decode("utf-8", errors="replace")
                            text = _parse_claude_json_line(raw)
                            if text:
                                output_lines.append(text)
                                sse_lines = text.split("\n")
                                sse = "\n".join(f"data: {l}" for l in sse_lines)
                                yield f"{sse}\n\n"
                        else:
                            chunk = await proc.stdout.read(4096)
                            if not chunk:
                                break
                            text = chunk.decode("utf-8", errors="replace")
                            output_lines.append(text)
                            lines = text.split("\n")
                            sse = "\n".join(f"data: {l}" for l in lines)
                            yield f"{sse}\n\n"

                    await proc.wait()

                    output_str = "".join(output_lines)
                    notes = extract_archi_notes(output_str)
                    if notes:
                        append_archi(track_id, notes)

                    # Auto-done — save archi notes as task notes so next task sees findings
                    if req.auto_done:
                        task_notes = notes[:600].strip() if notes else ""
                        complete_task(track_id, task_id, task_notes)

                    yield f"data: __TASK_DONE__\n\n"

                except Exception as e:
                    yield f"data: ⚠ Error in task {task_num}: {e}\n\n"

            yield f"data: __BULK_DONE__ {len(valid_task_ids)} tasks completed\n\n"

        return StreamingResponse(
            generate_bulk(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/archi")
    def get_archi():
        from core.scanner import get_global_archi, GLOBAL_ARCHI_PATH
        return {"content": get_global_archi(), "exists": GLOBAL_ARCHI_PATH.exists()}

    @app.get("/api/memory")
    def get_memory():
        from core.scanner import get_global_memory, GLOBAL_MEMORY_PATH
        return {"content": get_global_memory(), "exists": GLOBAL_MEMORY_PATH.exists()}

    @app.delete("/api/memory")
    def clear_memory():
        from core.scanner import GLOBAL_MEMORY_PATH
        if GLOBAL_MEMORY_PATH.exists():
            GLOBAL_MEMORY_PATH.unlink()
        return {"ok": True}

    @app.post("/api/tracks/{track_id}/spec/interview")
    async def stream_spec_interview(track_id: str, req: InterviewRequest):
        """One turn of the spec interview — streams LLM, signals __QUESTION__ or __SPEC_COMPLETE__."""
        from agents.analyst import INTERVIEW_PROMPT
        from core.track_manager import save_spec, update_track_phase
        from core.router import _build_command, _get_cli_for_model, get_model_for_phase

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        history_lines = []
        for item in req.qa:
            history_lines.append(f"Q: {item.get('q', '')}")
            history_lines.append(f"A: {item.get('a', '')}")
        history_section = "Previous Q&A:\n" + "\n".join(history_lines) if history_lines else ""

        prompt = INTERVIEW_PROMPT.format(
            description=req.description,
            history_section=history_section,
        )

        model = get_model_for_phase("spec", plan)
        cli = _get_cli_for_model(model)
        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")
        cmd = _build_command(cli, model, None, ["Read"])
        if cli == "claude":
            cmd += ["--output-format", "stream-json", "--verbose"]

        async def generate_interview():
            chunks: list[str] = []
            yield f"data: __META__ {model} | interview\n\n"
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    limit=10 * 1024 * 1024,  # 10 MB — Claude JSON lines can be large
                )
                proc.stdin.write(prompt.encode())
                await proc.stdin.drain()
                proc.stdin.close()
                while True:
                    if cli == "claude":
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        raw = line.decode("utf-8", errors="replace")
                        text = _parse_claude_json_line(raw)
                        if text:
                            chunks.append(text)
                            sse_lines = text.split("\n")
                            sse = "\n".join(f"data: {l}" for l in sse_lines)
                            yield f"{sse}\n\n"
                    else:
                        chunk = await proc.stdout.read(4096)
                        if not chunk:
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        chunks.append(text)
                        lines = text.split("\n")
                        sse = "\n".join(f"data: {l}" for l in lines)
                        yield f"{sse}\n\n"
                await proc.wait()
                output = "".join(chunks).strip()
                if "# Spec:" in output:
                    spec_start = output.find("# Spec:")
                    save_spec(track_id, output[spec_start:].strip())
                    update_track_phase(track_id, "plan")
                    log(track_id, "Spec written via interactive interview", "ANALYST")
                    yield "data: __SPEC_COMPLETE__\n\n"
                else:
                    yield "data: __QUESTION__\n\n"
            except Exception as e:
                yield f"data: ⚠ Error: {e}\n\n"
            finally:
                yield "data: __DONE__\n\n"

        return StreamingResponse(
            generate_interview(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/tracks/{track_id}/tasks/{task_id}/review")
    async def stream_task_review(track_id: str, task_id: str):
        """Stream code review — LLM reads files, outputs PASS or FAIL verdict."""
        from agents.reviewer import REVIEW_PROMPT
        from core.track_manager import get_spec
        from core.router import _build_command, _get_cli_for_model, get_model_for_phase, get_tools_for_phase

        plan = get_track(track_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        tasks = load_tasks(track_id)
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        spec = get_spec(track_id) or "(no spec)"
        prompt = REVIEW_PROMPT.format(
            spec=spec,
            task_title=task.get("title", ""),
            task_description=task.get("description", ""),
        )

        model = get_model_for_phase("review", plan)
        cli = _get_cli_for_model(model)
        if not shutil.which(cli):
            if cli != "claude" and shutil.which("claude"):
                cli = "claude"
                model = "claude-sonnet-4-6"
            else:
                raise HTTPException(status_code=500, detail=f"CLI '{cli}' not found")
        tools = get_tools_for_phase("review", plan)
        cmd = _build_command(cli, model, None, tools)
        if cli == "claude":
            cmd += ["--output-format", "stream-json", "--verbose"]

        async def generate_review():
            chunks: list[str] = []
            yield f"data: __META__ {model} | review\n\n"
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    limit=10 * 1024 * 1024,  # 10 MB — Claude JSON lines can be large
                )
                proc.stdin.write(prompt.encode())
                await proc.stdin.drain()
                proc.stdin.close()
                while True:
                    if cli == "claude":
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        raw = line.decode("utf-8", errors="replace")
                        text = _parse_claude_json_line(raw)
                        if text:
                            chunks.append(text)
                            sse_lines = text.split("\n")
                            sse = "\n".join(f"data: {l}" for l in sse_lines)
                            yield f"{sse}\n\n"
                    else:
                        chunk = await proc.stdout.read(4096)
                        if not chunk:
                            break
                        text = chunk.decode("utf-8", errors="replace")
                        chunks.append(text)
                        lines = text.split("\n")
                        sse = "\n".join(f"data: {l}" for l in lines)
                        yield f"{sse}\n\n"
                await proc.wait()
                output = "".join(chunks)
                if "## VERDICT: PASS" in output:
                    yield "data: __REVIEW_PASS__\n\n"
                elif "## VERDICT: FAIL" in output:
                    yield "data: __REVIEW_FAIL__\n\n"
            except Exception as e:
                yield f"data: ⚠ Error: {e}\n\n"
            finally:
                yield "data: __DONE__\n\n"

        return StreamingResponse(
            generate_review(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/tracks/{track_id}/tasks/{task_id}/rework")
    def create_rework(track_id: str, task_id: str, req: ReworkRequest):
        """Create a rework task from a failed review."""
        tasks = load_tasks(track_id)
        original = next((t for t in tasks if t["id"] == task_id), None)
        if not original:
            raise HTTPException(status_code=404, detail="Task not found")
        title = f"[REWORK] {original.get('title', 'Task')}"
        orig_desc = original.get("description", "")
        if req.review_issues:
            desc = f"{orig_desc}\n\nReview issues to fix:\n{req.review_issues}" if orig_desc else f"Review issues to fix:\n{req.review_issues}"
        else:
            desc = orig_desc
        task = add_task(track_id, title, desc)
        log(track_id, f"Rework task created for: {original.get('title', '')}", "REVIEW")
        return task

    # ── WebSocket terminal ────────────────────────────────────────────────

    @app.websocket("/ws/terminal")
    async def terminal_ws(websocket: WebSocket, token: str = None, cols: int = 220, rows: int = 50):
        init_cmd = _pending_terminal_inits.pop(token, None) if token else None
        await terminal_manager.handle(websocket, init_cmd=init_cmd, cols=cols, rows=rows)

    # ── Static files / SPA ───────────────────────────────────────────────

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return HTMLResponse("<h1>arche</h1><p>Static files not found.</p>")

    return app
