# arche
 
**arche** is a development orchestrator that keeps your project context alive between LLM sessions.

Most LLM CLIs (`claude`, `gemini`…) start fresh every time — no memory of past decisions, architecture choices, or completed work. arche solves this by maintaining a persistent **spec**, **architecture memory**, and **task queue** per track, and automatically feeding the full context to your LLM at every step.

---

## What arche does

- **Persistent context**: Every task sees the full history of previous work
- **Multi-track support**: Pause a feature to fix a bug, then resume with full context restored
- **Architecture memory**: Auto-growing cross-track knowledge that survives task completion
- **Task automation**: Spec Q&A + LLM task decomposition in one command
- **Web UI**: Real-time monitoring and command execution via embedded terminal
- **Model routing**: Intelligently routes to different LLM models based on task phase (spec, plan, dev, debug, doc)

---

## How it works

```
arche scan                       (optional, once per project)
  └── reads source files → calls LLM → writes .arche-storage/archi.md

arche track new "feat: JWT auth"
  └── spec qa       Q&A interview → spec.md
  └── spec refine   LLM rewrites spec into a precise document
  └── track plan    LLM decomposes spec → tasks.yaml

arche task run
  └── reads  spec.md + archi.md (global) + memory.md (cross-track) + archi.md (track) + done tasks + session log
  └── calls  claude / gemini with the full context via Router
  └── writes architecture decisions → tracks/{id}/archi.md AND memory.md
  └── logs   output → sessions/{date}.md

arche task done  →  next task (same context, richer each time)
```

---

## Workflow diagram

```
  YOUR PROJECT
  ┌─────────────────────────────────────────────────────────────┐
  │                                                             │
  │  arche init                                                 │
  │    └─ configure project + LLM models (once per project)    │
  │                                                             │
  │  ┌── TRACK ──────────────────────────────────────────────┐  │
  │  │                                                       │  │
  │  │  arche track new "feat: something"                    │  │
  │  │    │                                                  │  │
  │  │    ├─ [1] arche spec qa   ← Q&A → spec.md            │  │
  │  │    │        └─ arche spec refine  ← LLM refines       │  │
  │  │    │                                                  │  │
  │  │    └─ [2] arche track plan  ← LLM → tasks.yaml       │  │
  │  │                                                       │  │
  │  │  ┌── WORK LOOP ────────────────────────────────────┐  │  │
  │  │  │                                                 │  │  │
  │  │  │  arche task run                                 │  │  │
  │  │  │    ├─ context: spec + archi + done + log        │  │  │
  │  │  │    ├─ calls: claude / gemini                    │  │  │
  │  │  │    └─ writes: archi.md (architecture memory)   │  │  │
  │  │  │                                                 │  │  │
  │  │  │  arche task done  ──────────────────────────┐  │  │  │
  │  │  │                                             │  │  │  │
  │  │  │  arche task run  (next task, richer ctx) <──┘  │  │  │
  │  │  │                   ...until all done            │  │  │
  │  │  └────────────────────────────────────────────────┘  │  │
  │  │                                                       │  │
  │  │  arche track done                                     │  │
  │  └───────────────────────────────────────────────────────┘  │
  │                                                             │
  │  Multiple tracks can coexist — only one is ACTIVE at a time │
  └─────────────────────────────────────────────────────────────┘
```

---

## Requirements

- Python 3.11+
- At least one LLM CLI installed and authenticated:
  - [`claude`](https://docs.anthropic.com/en/docs/claude-code) (Claude Code)
  - [`gemini`](https://github.com/google-gemini/gemini-cli) (Gemini CLI)

---

## Installation

```bash
git clone <repo-url>
cd arche
make install-pipx       # installs arche globally via pipx (recommended)
```

> **On Debian/Ubuntu**: if pipx is not found, `make install-pipx` installs it automatically.

After installation, `arche` is available in any directory.

```bash
# To hack on arche itself (editable local install):
make install
source .venv/bin/activate
```

---

## Quick start

### The minimal path — 5 commands

```bash
cd ~/my-project
arche init                              # configure once
arche track new "feat: my feature"      # spec Q&A → tasks
arche task run                          # run current task → LLM
arche task done                         # mark done, next task
arche track done                        # track complete
```

That's it. Repeat `task run` / `task done` until all tasks are done.

### Step-by-step detail

**1. Initialize (once per project)**

```bash
cd ~/my-project
arche init
```

Prompts for: project name, stack/languages, which LLM model per phase.
Creates `.arche-storage/project.yaml`.

**2. Create a track**

A **track** is a self-contained unit of work: a feature, bug fix, refactor, or documentation pass.

```bash
arche track new "feat: user authentication"
```

arche runs three steps automatically:
1. **Spec Q&A** — answers your questions and writes `spec.md`
2. **LLM spec refinement** — rewrites the raw answers into a precise requirements document
3. **Task generation** — LLM decomposes the spec into an ordered task list

**3. Run tasks**

```bash
arche task run        # builds full context → calls LLM → streams output
arche task done       # mark done, move to next task
arche task run        # next task — context now includes previous work
...
arche track done      # track complete
```

**4. Web UI (optional)**

```bash
arche web             # starts at http://localhost:7331
arche web-start       # initialize project (if needed) then start web UI
```

---

## Scenarios

### Scenario 1 — New feature from scratch

```bash
cd ~/my-project
arche init

arche track new "feat: stripe payment integration"
# → Q&A: goal, context, requirements, constraints
# → LLM refines spec
# → LLM generates 8 tasks

arche task run        # "1. Add stripe dependency and env config"
arche task done
arche task run        # "2. Create PaymentService class"
arche task done
# ... repeat
arche track done
```

Each `task run` automatically includes what was built in previous tasks via `archi.md`.

---

### Scenario 2 — Interrupt a feature for an urgent bug

```bash
# You are mid-feature
arche track new "feat: oauth integration"
arche task run        # working on task 3/7

# Urgent bug reported in production
arche track new "fix: null pointer login"   # feat is now PAUSED automatically
arche task run                               # debug context loaded
arche task done
arche track done                             # bug fixed

# Resume feature — context fully restored
arche track switch oauth
arche task run        # picks up exactly at task 3/7
```

```
arche track list

  Status    Track                       Progress
  ───────────────────────────────────────────────
  ACTIVE    feat/oauth-integration      ████░░░░   3/7
  PAUSED    fix/null-pointer-login      ████████   3/3  DONE
```

---

### Scenario 3 — Refine spec before planning

You want to write the spec carefully before generating tasks:

```bash
arche track new "feat: realtime notifications" --skip-planner
# → Q&A → spec written, no tasks yet

arche spec show         # review what was written
arche spec refine       # LLM improves the spec further

# Iterate until satisfied
arche spec qa           # redo the Q&A if needed

# Generate tasks when ready
arche track plan
```

---

### Scenario 4 — Manual tasks, no LLM planning

You already know exactly what to do:

```bash
arche track new "chore: update dependencies" --skip-analyst --skip-planner

arche task add "Update all pip packages"
arche task add "Run test suite"
arche task add "Update CHANGELOG"

arche task run
arche task done
# ...
```

---

### Scenario 5 — Debug a specific error

```bash
arche track new "fix: UserService NPE on login"

arche debug "NullPointerException at UserService.java:42 — user.getProfile() returns null"
# → LLM analyses the error with full project context → suggests fix

arche task run    # implement the fix
arche task done
arche track done
```

---

### Scenario 6 — Documentation pass

```bash
arche track new "doc: API documentation"

arche task run    # LLM generates docs using Gemini (large context, 1M tokens)
arche task done
arche track done
```

Or target a specific path:

```bash
arche doc src/api/     # one-shot doc generation for a directory
```

---

### Scenario 7 — Review and rework spec mid-track

You realize the spec is incomplete after seeing the generated tasks:

```bash
arche track new "feat: multi-tenant support"
# tasks generated, but scope is too broad

arche spec show         # read the current spec
arche spec refine       # ask LLM to sharpen it

arche track plan --force   # regenerate tasks from updated spec
```

---

### Scenario 8 — Jump to a specific task

```bash
arche task list
#  ✓ [a1b2] Setup database schema
#  ✓ [c3d4] Create User model
#  ▶ [e5f6] Add authentication middleware   ← current
#  · [g7h8] Write unit tests
#  · [i9j0] Update API docs

arche task switch 4         # by position
arche task switch g7        # by id prefix
arche task switch "unit"    # by title substring
```

---

### Scenario 9 — Unblock a stuck task

```bash
arche task run
# LLM output is ambiguous, waiting for external decision

arche task block "waiting for DB schema decision from team"

# Later, once unblocked:
arche task switch 3       # come back to it
arche task run
```

---

### Scenario 10 — Multi-project, one arche

arche is per-project (each project has its own `.arche-storage/`), but you can have multiple terminal tabs or windows:

```bash
# Tab 1 — project A
cd ~/projects/api
arche task run

# Tab 2 — project B
cd ~/projects/frontend
arche task run
```

Each project manages its own tracks independently.

---

## Command reference

### Status

```bash
arche                     # full status: active track + all tasks
arche track list          # all tracks with progress bars
arche task list           # all tasks in the active track
arche resume              # same as arche (no args)
```

### Setup

```bash
arche init                # configure project + LLM model choices
arche scan                # scan source files → .arche-storage/archi.md (optional, re-runnable)
arche web [--port 7331]   # web UI with embedded terminal
arche help                # full interactive command guide
```

### Tracks

```bash
arche track new "feat: …"                    # Q&A → spec → tasks (all-in-one)
arche track new "feat: …" --no-refine        # skip LLM spec refinement
arche track new "feat: …" --skip-analyst     # skip Q&A, empty spec
arche track new "feat: …" --skip-planner     # skip task generation
arche track list                             # list all tracks
arche track switch <id|name>                 # switch active track
arche track plan                             # generate tasks from existing spec
arche track plan --force                     # regenerate tasks (clears existing)
arche track done                             # mark track as complete
arche track help                             # track command reference
```

### Spec

```bash
arche spec qa                 # Q&A interview → spec + LLM refinement
arche spec qa --no-refine     # Q&A only, skip LLM refinement
arche spec refine             # refine existing spec with LLM (no Q&A)
arche spec show               # display the current spec
arche spec help               # spec command reference
```

### Tasks — the main loop

```bash
arche task run                  # ★ run current task with full context → LLM
arche task run --auto-done      #   same + mark DONE automatically
arche task next                 #   pick next pending task (without running)
arche task switch <n|id|title>  #   jump to a specific task
arche task done [--notes "…"]  #   mark done, advance to next
arche task block "reason"       #   mark current task as blocked
arche task add "title"          #   add a task manually
arche task list                 #   list all tasks
arche task help                 #   task command reference
```

### Memory

```bash
arche memory show         # display the shared cross-track memory
arche memory clear        # clear the shared cross-track memory
```

### Ad-hoc agents

```bash
arche dev "instruction"   # free-form coding with full track context
arche debug "error"       # analyse error + fix suggestion
arche doc [path]          # generate documentation (uses Gemini for large context)
arche log "note"          # add a manual note to the session journal
```

---

## How context is built

Every `arche task run` assembles a prompt from these layers, in order:

| Layer | Source | Content |
|-------|--------|---------|
| 1 | `spec.md` | Track goal and requirements |
| 2 | `.arche-storage/archi.md` | Global blueprint — generated by `arche scan` (static) |
| 3 | `.arche-storage/memory.md` | **Cross-track memory** — discoveries shared across all tracks (auto-grows) |
| 4 | `tracks/{id}/archi.md` | Track-specific architecture notes (auto-grows) |
| 5 | Done tasks | What was completed (with notes) |
| 6 | Pending tasks | What comes next |
| 7 | Session log | Recent session entries (last ~1500 chars) |

After each run, the LLM response is scanned for an **"Architecture notes"** section. If found, it is appended to both `tracks/{id}/archi.md` (track-scoped) and `.arche-storage/memory.md` (shared across all tracks, with track attribution). This is what makes context accumulate — each task leaves a trace for the next one, and discoveries cross track boundaries automatically.

---

## Storage layout

All state lives in `.arche-storage/` at your project root. Plain text — readable and committable.

```
.arche-storage/
├── project.yaml              ← project name, stack, LLM model config
├── current.yaml              ← pointer to the active track
├── archi.md                  ← global project blueprint (generated by arche scan)
├── memory.md                 ← cross-track memory (auto-updated after every task run)
└── tracks/
    └── {track-id}/
        ├── meta.yaml         ← track name, status, phase, dates
        ├── spec.md           ← goal and requirements
        ├── archi.md          ← track-specific architecture notes (auto-updated)
        ├── tasks.yaml        ← tasks with statuses and notes
        └── sessions/
            └── {date}.md     ← session journal with full LLM output
```

> **Tip:** commit `.arche-storage/` to your repository. The accumulated context is valuable and survives machine changes.

---

## LLM model routing

arche routes to different models depending on the work phase:

| Phase | Default model | Rationale |
|-------|--------------|-----------|
| `spec` | `claude-opus-4-6` | Deep reasoning for requirements |
| `plan` | `claude-sonnet-4-6` | Architecture decomposition |
| `dev` | `claude-sonnet-4-6` | Code generation |
| `debug` | `claude-sonnet-4-6` | Error analysis |
| `doc` | `gemini-2.0-flash` | Large context (1M tokens) |
| `review` | `claude-haiku-4-5` | Fast lightweight review |

Choose models during `arche init`. Override per-track in `.arche-storage/tracks/{id}/meta.yaml`.

---

## Web UI

```bash
arche web
```

Opens at `http://localhost:7331`. Three areas:

**Sidebar** — all tracks with status badges and progress bars.

**Main panel** — four tabs:
- **Spec** — track spec in markdown. Button to generate tasks from spec.
- **Tasks** — task list with filter and action toolbar (run, done, block, edit).
- **Sessions** — session journal, expandable entries.
- **Output** — streaming LLM output during task runs.

**Console** — embedded terminal (xterm.js). Run any `arche` command here. Multiple tabs supported.

---

## Architecture

arche is modular and organized into three main layers: **CLI**, **Core Engine**, and **Web Interface**. All components communicate through plain text storage in `.arche-storage/`.

### Layer 1: CLI (`arche.py`)

**Entry point**: `arche.py` using the **Typer** framework. Implements command groups:
- `arche` — global status (shows active track + tasks)
- `track` — create, list, switch, mark done
- `task` — run, done, block, add, list, switch
- `spec` — Q&A, refine, show
- `memory` — view/clear cross-track memory
- Ad-hoc: `dev`, `debug`, `doc`, `log`, `scan`, `init`

Each command validates project state and delegates to **Core** functions.

### Layer 2: Core Engine

The orchestration logic lives in `core/`:

#### **`track_manager.py`** — Track lifecycle
- CRUD: `new_track()`, `get_track()`, `list_tracks()`, `switch_track()`, `mark_track_done()`
- Persistence: loads/saves `project.yaml`, `current.yaml`, and track metadata
- Slugifies track names, generates UUIDs, manages track status (ACTIVE, PAUSED, DONE)
- Backward-compatible aliases: `plan_manager.py` exports these as `*_plan()` functions

#### **`task_engine.py`** — Task queue
- CRUD: `add_task()`, `load_tasks()`, `save_tasks()`, `start_task()`, `complete_task()`
- Status tracking: TODO, IN_PROGRESS, DONE, BLOCKED
- Persists to `tracks/{id}/tasks.yaml`
- Supports per-task notes and phase filtering

#### **`context.py`** — Context builder
- **`build_task_prompt()`** — assembles the complete prompt for a task by stacking 7 context layers:
  1. Track spec
  2. Global architecture (from scanner)
  3. Cross-track memory (from previous tasks)
  4. Track-specific architecture
  5. Completed tasks (with notes)
  6. Pending tasks
  7. Session log (recent entries)
- **`append_archi()`** — adds architecture notes to both track-local and global memory after LLM runs

#### **`scanner.py`** — Project analysis
- **`arche scan`**: reads source tree, filters (ignore `.git`, `node_modules`, etc.), calls LLM to generate `archi.md`
- Maintains `GLOBAL_ARCHI_PATH` (static project blueprint) and `GLOBAL_MEMORY_PATH` (auto-growing cross-track knowledge)

#### **`router.py`** — LLM dispatch
- **`call_llm()`** — routes prompts to the right CLI (claude or gemini) with the right model
- **Phase-based routing**: each phase (spec, plan, dev, debug, doc) is assigned a default model
- **Tool grants**: phase determines which tools (Read, Write, Bash) are available to Claude Code
- **ModelRegistry**: reads from `.arche-storage/model_registry.yaml` (if present) to support custom model setups
- Falls back to hardcoded defaults if registry unavailable

#### **`session_logger.py`** — Session journaling
- Logs all LLM calls to `tracks/{id}/sessions/{date}.md`
- Persists conversation history for audit and context retrieval

#### **`status.py`** — Display formatting
- Rich table rendering of tracks, tasks, and progress
- Shows status badges, progress bars, and summaries

### Layer 3: Agents (`agents/`)

**Specialized workers** that build prompts and call the LLM:

- **`analyst.py`** (spec qa) — Q&A interviewer. Asks clarifying questions, refines spec.
- **`planner.py`** (track plan) — Task decomposer. Reads spec, generates task list.
- **`developer.py`** (task run) — Code generation. Executes current task with full context.
- **`debugger.py`** (debug) — Error analyzer. Analyzes stack traces and suggests fixes.
- **`documenter.py`** (doc) — Doc generator. Generates markdown docs (uses Gemini for large context).
- **`reviewer.py`** (review) — Code reviewer. Lightweight feedback on changes.

All agents:
1. Build a prompt using `context.build_task_prompt()` + phase-specific instructions
2. Call `router.call_llm()` to delegate to the appropriate LLM
3. Extract **architecture notes** from the output (optional "Architecture notes:" section)
4. Call `context.append_archi()` to persist notes to both track and global memory
5. Log the session

### Layer 4: Web Interface (`web/`)

**`server.py`** — FastAPI application:
- REST endpoints: `/api/tracks`, `/api/tasks`, `/api/sessions`
- Real-time: WebSocket at `/api/terminal` for embedded xterm
- Static frontend: served from `web/static/`
- Terminal emulation: `ptyprocess` spawns subprocess pseudo-terminals, bridges to WebSocket

**`ws_terminal.py`** — Terminal manager:
- Handles multiple terminal tabs (indexed by UUID)
- Bridges pty I/O to WebSocket messages

### Data Flow: `arche task run`

```
1. CLI: "arche task run"
2. arche.py calls developer.run(track_id, instruction)
3. developer.py:
   a. Calls context.build_task_prompt() → 7-layer prompt
   b. Calls router.call_llm(prompt, phase="dev") → spawns CLI subprocess
   c. Streams output to console (rich.Console)
   d. Extracts architecture notes from output
4. context.append_archi(archi_notes)
   a. Appends to tracks/{id}/archi.md (track-local)
   b. Appends to .arche-storage/memory.md (global, with track attribution)
5. session_logger.log() records output and notes
6. CLI exits, next `task run` has richer context
```

### Storage Schema

```
.arche-storage/
├── project.yaml              ← project config (name, stack, model choices)
├── model_registry.yaml       ← (optional) custom LLM model routing
├── current.yaml              ← pointer to active track ID
├── archi.md                  ← global project blueprint (static)
├── memory.md                 ← auto-growing cross-track knowledge
└── tracks/
    └── {track-id}/
        ├── meta.yaml         ← track name, status (ACTIVE/PAUSED/DONE), phase, dates
        ├── spec.md           ← goal and requirements (written by analyst)
        ├── archi.md          ← track-specific architecture notes (auto-appended after each task)
        ├── tasks.yaml        ← tasks with IDs, statuses, and notes
        └── sessions/
            └── {YYYY-MM-DD}.md ← session log with all LLM outputs
```

All files are plain text — readable, auditable, and committable.

### Design Principles

1. **Context accumulation**: Every task leaves traces (archi notes) for the next task.
2. **No LLM library**: arche invokes Claude Code or Gemini CLIs directly via subprocess. Full tool grants (Read, Write, Bash) are available to Claude Code in dev/debug phases.
3. **Plain text state**: No databases. All config and memory is version-controllable.
4. **Fallback mode**: If a model is unavailable, arche falls back to defaults or manual overrides.
5. **Multi-model routing**: Different phases use different models to optimize cost/speed/quality.

---

## FAQ

**Where do I run `arche init`?**
In the root of the project you are developing. Each project has its own `.arche-storage/` directory.

**Can I use arche with any language or framework?**
Yes. arche is language-agnostic. Specify your stack during `arche init` so the LLM prompt is accurate.

**What if the LLM CLI is not found?**
arche reports which CLI it expected and falls back to `claude` if available. Make sure your LLM CLI is in `PATH`.

**Can I edit spec or tasks manually?**
Yes. `spec.md` and `tasks.yaml` are plain files. Edit them directly. Use `arche spec show` to read, `arche track plan --force` to regenerate tasks after manual spec edits.

**Is `.arche-storage/` safe to commit?**
Yes, and recommended. Plain text, no secrets. Committing it means context survives machine changes and is shareable with teammates.

**I already have tasks — can I add more?**
Yes: `arche task add "new task title"`. Tasks are appended to the list.

**Can I skip the Q&A and write the spec myself?**
Yes: `arche track new "..." --skip-analyst`, then edit `.arche-storage/tracks/{id}/spec.md` directly, then `arche track plan`.

---

## Contributing & Development

### Setting up for local development

```bash
git clone <repo-url>
cd arche
make install              # creates .venv and installs in editable mode
source .venv/bin/activate
```

### Running tests and checks

```bash
make check                # validates Python syntax across all modules
```

### Project structure for developers

- **`arche.py`** — CLI entry point (Typer commands)
- **`core/`** — Orchestration logic (track, task, context, LLM routing)
- **`agents/`** — Specialized LLM workers (analyst, developer, debugger, etc.)
- **`web/`** — FastAPI server + WebSocket terminal
- **`.arche-storage/`** — Example/fixture data for manual testing
- **`Makefile`** — Installation, venv, syntax checking

### Key concepts for contributors

1. **Track = unit of work**: Each track has its own spec, tasks, and architecture notes.
2. **Context layers**: Every task prompt is built from 7 stacked layers (see `context.py`).
3. **Architecture notes**: LLM outputs are scanned for an "Architecture notes:" section. If found, they're persisted to both track-local and global memory.
4. **No persistent state beyond `.arche-storage/`**: No databases or caches. All state is committed to `.arche-storage/`.
5. **Plain CLI invocation**: arche does NOT import LLM libraries. It spawns `claude` or `gemini` CLIs as subprocesses.

### Adding a new agent

1. Create `agents/my_agent.py` with a `run(track_id, track_meta, instruction: str) -> str` function.
2. Use `context.build_task_prompt()` to assemble the context.
3. Call `router.call_llm(prompt, phase="...", track_meta=track_meta)` to invoke the LLM.
4. Extract and persist architecture notes:
   ```python
   from core.context import extract_archi_notes, append_archi
   archi_notes = extract_archi_notes(result)
   if archi_notes:
       append_archi(track_id, archi_notes)
   ```
5. Log the session: `session_logger.log(track_id, description, phase)`
6. Wire the command into `arche.py` using Typer.

### Modifying the context builder

If you want to change how context is assembled, edit `context.py:build_task_prompt()`. The function returns a markdown string with 7 sections:
1. Project info
2. Track spec
3. Global architecture
4. Global memory (cross-track)
5. Track architecture
6. Completed tasks
7. Pending tasks
8. Session log

You can insert additional sections or reorder as needed.

---

## Troubleshooting

### "No active track" when running `arche task run`

Create a track first:
```bash
arche track new "feat: my feature"
```

### LLM CLI not found

Make sure your LLM CLI (e.g., `claude`) is installed and in your `PATH`:
```bash
which claude     # should return the path to the CLI
claude --help    # should show help text
```

If not installed:
- Claude Code: [docs.anthropic.com](https://docs.anthropic.com/en/docs/claude-code)
- Gemini CLI: [github.com/google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)

### Web UI won't start

Check if port 7331 is in use:
```bash
lsof -i :7331    # list processes using port 7331
arche web --port 8000  # use a different port
```

### Large context truncation

If your prompt gets truncated, arche prioritizes layers in this order:
1. Current task (never truncated)
2. Spec
3. Global architecture
4. Global memory (recent)
5. Track architecture
6. Completed tasks (oldest first)

Reduce context by cleaning up old session logs or archiving completed tracks.

### Restore a paused track

```bash
arche track list     # see all tracks
arche track switch <id>  # switch to paused track
arche task run       # resumes at the last task
```

---

## License

MIT — see LICENSE file for details.
