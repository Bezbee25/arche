# Architecture — arche

> Development orchestrator that maintains persistent context (spec, architecture memory, task queue) across multiple LLM sessions, enabling stateful multi-step feature development without losing decisions or progress.

## Stack

**Language**: Python 3.11+ | **CLI Framework**: Typer 0.9+ | **Web Server**: FastAPI 0.110+ / Uvicorn 0.29+ | **Terminal UI**: Rich 13.7+ | **Storage**: YAML (PyYAML 6.0+) | **WebSocket**: websockets 12.0+ | **Terminal Multiplexing**: ptyprocess 0.7+

**No embedded LLM**: invokes external CLIs (`claude`, `gemini`, `codex`) via subprocess; models configured per phase.

## Structure

```
arche/
├── arche.py              Main CLI entry point (Typer app)
├── core/                 State management & orchestration
│   ├── track_manager.py  Track/plan CRUD, active track, metadata
│   ├── task_engine.py    Task queue (TODO/IN_PROGRESS/DONE/BLOCKED)
│   ├── context.py        Rich prompt assembly (spec + archi + session log)
│   ├── router.py         LLM dispatch (phase → model → CLI binary)
│   ├── session_logger.py Daily session journal per track
│   ├── scanner.py        Project scanner → storage/archi.md
│   ├── status.py         Terminal UI (track list, progress bars)
│   └── plan_manager.py   Backward-compat shim (plan → track)
├── agents/               LLM-delegated tasks (prompts + control flow)
│   ├── analyst.py        Q&A interview → spec.md (interactive)
│   ├── planner.py        spec.md → tasks.yaml
│   ├── developer.py      Code generation with full context
│   ├── debugger.py       Error analysis & fix suggestion
│   ├── documenter.py     Generate docs from spec + source
│   └── reviewer.py       Code review verdict (PASS/FAIL)
├── web/                  Web UI + WebSocket terminal
│   ├── server.py         FastAPI routes (tracks, tasks, bulk-run, streaming)
│   ├── ws_terminal.py    WebSocket ↔ PTY bridge
│   └── static/           HTML/CSS/JS frontend (task checkboxes, output panel)
└── storage/              Persistent data (created per project)
    ├── project.yaml      Project config, stack, LLM model assignments
    ├── current.yaml      Active track ID
    ├── archi.md          Global architecture memory (all tracks)
    └── tracks/{id}/
        ├── meta.yaml     Track metadata (name, phase, status, models)
        ├── spec.md       Requirements document
        ├── tasks.yaml    Task queue with statuses
        ├── archi.md      Track-specific architecture notes
        └── sessions/     Daily logs (YYYY-MM-DD.md)
```

## Entry Points

**CLI**: `arche.py` → Typer app with command groups: `arche track`, `arche task`, `arche spec`, `arche memory`

**Web**: `arche web` → FastAPI server on `:7331` with static SPA (HTML/JS) + WebSocket for live terminal output

**Project Init**: `arche init` → prompts for project name, stack, LLM model assignments (stored in `storage/project.yaml`)

## Key Modules & Responsibilities

| Module | Purpose |
|--------|---------|
| **track_manager** | CRUD tracks, switch active, persist metadata (status, phase, created_at) |
| **task_engine** | Load/save task queue; track status (TODO, IN_PROGRESS, DONE, BLOCKED); resolve tasks by index/ID/title substring |
| **context** | Assemble rich prompt: spec + global archi + track archi + session log + done tasks + pending tasks |
| **router** | Route phase → LLM model (Claude/Gemini) → CLI binary; grant tools per phase (Read/Write/Edit/Bash) |
| **analyst** | Interactive Q&A interview → spec.md; LLM refinement of raw answers |
| **planner** | LLM decomposes spec → numbered task list; optional phase grouping |
| **developer** | Delegate coding task with full context; extract & persist architecture notes to archi.md |
| **session_logger** | Append timestamped entries to daily session journal per track |
| **scanner** | Scan project files → summarize for LLM → generate storage/archi.md (one-time) |
| **server** | FastAPI routes: track/task CRUD, spec, task run/done, bulk-run streaming, WebSocket terminal |

## Patterns & Conventions

**Status Lifecycle**: Tasks flow TODO → IN_PROGRESS → DONE (or BLOCKED). Statuses persist in `tasks.yaml`.

**Context Accumulation**: Each `task run` includes previous DONE tasks in the prompt so LLM understands implemented decisions.

**Architecture Memory**: LLM annotations in task output are extracted (enclosed in `<!-- ARCH: ... -->` markers) and appended to both track-local `archi.md` and global `storage/archi.md` for cross-track reference.

**Session Journaling**: All LLM calls, task transitions, blocks logged with timestamp to `sessions/YYYY-MM-DD.md` per track.

**Phase Model**: Each task phase (spec, think, plan, arch, dev, debug, doc, review) has assigned Claude/Gemini model + tool permissions.

**Bulk Operations** (CLI/Web): `arche task switch --bulk 1,2,3` or API `POST /api/tracks/{id}/tasks/bulk-run` executes multiple tasks in sequence, auto-marking DONE, with streaming output.

**Track Types**: Default "task" (normal workflow); "task/debug" generates template tasks (no LLM); "task/doc" for documentation passes.

## Data Flow

```
User Input (CLI/Web)
  ↓
[arche.py] → Typer router
  ↓
[agents/] → LLM delegation via [router]
  ├─ call_llm(prompt, phase, track_meta, stream=True)
  │   → [router.call_llm] → subprocess to CLI binary (claude/gemini)
  │   → stdout streaming to terminal / WebSocket
  ├─ extract_archi_notes(output) → [context.append_archi]
  └─ output logged to [session_logger]
  ↓
State Updates
  ├─ [track_manager] → meta.yaml (phase, status)
  ├─ [task_engine] → tasks.yaml (task status)
  ├─ [context] → archi.md (architecture decisions)
  └─ [session_logger] → sessions/YYYY-MM-DD.md
  ↓
Web UI (optional)
  ├─ [server] FastAPI routes
  ├─ [ws_terminal] WebSocket → PTY (live terminal output)
  └─ [app.js] SPA: task checkboxes, bulk-run UI, output panel
```

## External Services

**LLM CLIs** (required, external binary): `claude`, `gemini`, `codex` — invoked via subprocess with auth managed by respective tools.

**No databases**: uses local filesystem YAML storage (`storage/`); persists across sessions automatically.

**No cloud services**: self-contained; suitable for offline use.

## Configuration

**Per-Project** (`storage/project.yaml`):
```yaml
name: "My Project"
stack: "Python 3.11 + FastAPI"
models:
  spec: "claude-opus-4-6"
  dev: "claude-sonnet-4-6"
  doc: "gemini-2.0-flash"
tools:
  dev: ["Read", "Write", "Edit", "Bash"]
```

**Per-Track** (`storage/tracks/{id}/meta.yaml`): name, status (ACTIVE/PAUSED/DONE), phase, created_at, optional phase-specific model overrides.

**Environment**: None required; LLM authentication delegated to external CLI tools (`~/.claude/config`, `~/.gemini/config`).
