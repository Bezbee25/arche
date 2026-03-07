# arche

**arche** is a development orchestrator that keeps your project context alive between LLM sessions.

Most LLM CLIs (`claude`, `gemini`…) start fresh every time — no memory of past decisions, architecture choices, or completed work. arche solves this by maintaining a persistent **spec**, **architecture memory**, and **task queue** per track, and automatically feeding the full context to your LLM at every step.

---

## How it works

```
arche scan                       (optional, once per project)
  └── reads source files → calls LLM → writes storage/archi.md

arche track new "feat: JWT auth"
  └── spec qa       Q&A interview → spec.md
  └── spec refine   LLM rewrites spec into a precise document
  └── track plan    LLM decomposes spec → tasks.yaml

arche task run
  └── reads  spec.md + archi.md (global) + memory.md (cross-track) + archi.md (track) + done tasks + session log
  └── calls  claude / gemini with the full context
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
Creates `storage/project.yaml`.

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

arche is per-project (each project has its own `storage/`), but you can have multiple terminal tabs or windows:

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
arche scan                # scan source files → storage/archi.md (optional, re-runnable)
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
| 2 | `storage/archi.md` | Global blueprint — generated by `arche scan` (static) |
| 3 | `storage/memory.md` | **Cross-track memory** — discoveries shared across all tracks (auto-grows) |
| 4 | `tracks/{id}/archi.md` | Track-specific architecture notes (auto-grows) |
| 5 | Done tasks | What was completed (with notes) |
| 6 | Pending tasks | What comes next |
| 7 | Session log | Recent session entries (last ~1500 chars) |

After each run, the LLM response is scanned for an **"Architecture notes"** section. If found, it is appended to both `tracks/{id}/archi.md` (track-scoped) and `storage/memory.md` (shared across all tracks, with track attribution). This is what makes context accumulate — each task leaves a trace for the next one, and discoveries cross track boundaries automatically.

---

## Storage layout

All state lives in `storage/` at your project root. Plain text — readable and committable.

```
storage/
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

> **Tip:** commit `storage/` to your repository. The accumulated context is valuable and survives machine changes.

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

Choose models during `arche init`. Override per-track in `storage/tracks/{id}/meta.yaml`.

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

## FAQ

**Where do I run `arche init`?**
In the root of the project you are developing. Each project has its own `storage/` directory.

**Can I use arche with any language or framework?**
Yes. arche is language-agnostic. Specify your stack during `arche init` so the LLM prompt is accurate.

**What if the LLM CLI is not found?**
arche reports which CLI it expected and falls back to `claude` if available. Make sure your LLM CLI is in `PATH`.

**Can I edit spec or tasks manually?**
Yes. `spec.md` and `tasks.yaml` are plain files. Edit them directly. Use `arche spec show` to read, `arche track plan --force` to regenerate tasks after manual spec edits.

**Is `storage/` safe to commit?**
Yes, and recommended. Plain text, no secrets. Committing it means context survives machine changes and is shareable with teammates.

**I already have tasks — can I add more?**
Yes: `arche task add "new task title"`. Tasks are appended to the list.

**Can I skip the Q&A and write the spec myself?**
Yes: `arche track new "..." --skip-analyst`, then edit `storage/tracks/{id}/spec.md` directly, then `arche track plan`.
