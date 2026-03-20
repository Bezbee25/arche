SHELL  := /bin/bash
PYTHON := python3
VENV   := .venv
BIN    := $(VENV)/bin

.PHONY: help install install-pipx dev check clean uninstall

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  arche — multi-plan development orchestrator"
	@echo ""
	@echo "  ╔══════════════════════════════════════════════════════════════╗"
	@echo "  ║  Installation (once, from this directory)                   ║"
	@echo "  ╠══════════════════════════════════════════════════════════════╣"
	@echo "  ║  make install-pipx   ← RECOMMENDED                         ║"
	@echo "  ║    pipx creates an isolated venv; 'arche' available         ║"
	@echo "  ║    system-wide without any activation step.                 ║"
	@echo "  ╠══════════════════════════════════════════════════════════════╣"
	@echo "  ║  make install        local .venv/ ← DEV (hack on arche)    ║"
	@echo "  ╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  Quick start (full workflow):"
	@echo "    cd ~/my-project"
	@echo "    arche init                       # 1. configure project + LLM models"
	@echo "    arche track new \"feat: my feature\" # 2. spec Q&A → tasks generated automatically"
	@echo "    arche task run                   # 3. run current task via LLM"
	@echo "    arche task done                  #    mark done, advance to next task"
	@echo "    arche task run                   #    (repeat until all tasks done)"
	@echo "    arche track done                  # 4. track complete"
	@echo "    arche web                        # web UI on http://localhost:7331"
	@echo ""
	@echo "  Note: 'arche track new' runs spec Q&A + task generation in one shot."
	@echo "        Use 'arche spec' / 'arche spec --refine' to update the spec afterwards."
	@echo ""
	@echo "  Task management:"
	@echo "    arche task next                  # pick next pending task"
	@echo "    arche task switch <n|id|title>   # jump to a specific task"
	@echo "    arche task block <reason>        # mark current task blocked"
	@echo "    arche task add <title>           # add a task manually"
	@echo "    arche task list                  # list all tasks"
	@echo "    arche task help                  # full task command reference"
	@echo ""
	@echo "  Track management:"
	@echo "    arche track list                  # list all tracks"
	@echo "    arche track switch <id>           # switch active track"
	@echo "    arche track done                  # mark active track done"
	@echo "    arche track help                  # full track command reference"
	@echo ""
	@echo "  Agents (ad-hoc):"
	@echo "    arche spec qa                   # Q&A → spec + LLM refinement"
	@echo "    arche spec qa --no-refine       # Q&A only, skip LLM refinement"
	@echo "    arche spec refine               # refine existing spec with LLM"
	@echo "    arche spec show                 # display current spec"
	@echo "    arche dev \"what to implement\"   # delegate a coding task to LLM"
	@echo "    arche debug \"error message\"     # analyze error, get fix"
	@echo "    arche doc [path]                 # generate documentation"
	@echo ""
	@echo "  Misc:"
	@echo "    arche resume                     # show current state"
	@echo "    arche log \"note\"                # add note to session journal"
	@echo ""
	@echo "  Other targets:"
	@echo "    make check      Check Python syntax"
	@echo "    make clean      Remove .venv/ and temp files"
	@echo "    make uninstall  Uninstall arche (pipx)"
	@echo ""

# ── Global install via pipx ───────────────────────────────────────────────────
# pipx installs arche in an isolated venv and exposes 'arche' in PATH.
# Required on Debian/Ubuntu (PEP 668 blocks pip --user).
install-pipx:
	@echo "  → Checking pipx..."
	@if ! command -v pipx >/dev/null 2>&1; then \
		echo "  → pipx not found, installing..."; \
		if command -v apt >/dev/null 2>&1; then \
			sudo apt install -y pipx 2>/dev/null || \
			$(PYTHON) -m pip install pipx --break-system-packages --quiet --force; \
		else \
			$(PYTHON) -m pip install pipx --break-system-packages --quiet --force; \
		fi; \
		$(PYTHON) -m pipx ensurepath; \
		echo "  ⚠  Restart your shell or run: source ~/.bashrc"; \
	fi
	@echo "  → Installing arche via pipx..."
	pipx install --force --editable . 2>/dev/null || pipx install .
	@echo ""
	@echo "  ✓ arche installed globally via pipx"
	@echo ""
	@echo "  From any project:"
	@echo "    cd ~/my-project && arche init"
	@echo ""

# ── Local install in .venv/ (to develop arche itself) ────────────────────────
install: venv
	$(BIN)/pip install -e . --quiet
	@echo ""
	@echo "  ✓ arche installed (editable) in $(VENV)/"
	@echo ""
	@echo "  Activate : source $(VENV)/bin/activate"
	@echo "  Or run   : $(CURDIR)/$(VENV)/bin/arche <command>"
	@echo ""

# ── Local venv ────────────────────────────────────────────────────────────────
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "  → Creating venv in $(VENV)/"; \
		$(PYTHON) -m venv $(VENV); \
		$(BIN)/pip install --upgrade pip --quiet; \
		$(BIN)/pip install -r requirements.txt --quiet; \
		echo "  ✓ venv created and dependencies installed"; \
	else \
		echo "  ✓ venv already exists"; \
	fi

dev: install

# ── Syntax check ──────────────────────────────────────────────────────────────
check:
	@echo "  → Checking Python syntax..."
	@$(PYTHON) -m py_compile \
		arche.py \
		core/plan_manager.py \
		core/task_engine.py \
		core/session_logger.py \
		core/context.py \
		core/scanner.py \
		core/status.py \
		core/router.py \
		agents/analyst.py \
		agents/planner.py \
		agents/developer.py \
		agents/debugger.py \
		agents/documenter.py \
		web/server.py \
		web/ws_terminal.py
	@echo "  ✓ all files OK"

# ── Clean ─────────────────────────────────────────────────────────────────────
clean:
	@echo "  → Removing venv and temp files..."
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "  ✓ cleaned"

# ── Uninstall ─────────────────────────────────────────────────────────────────
uninstall:
	@if command -v pipx >/dev/null 2>&1 && pipx list 2>/dev/null | grep -q arche; then \
		pipx uninstall arche && echo "  ✓ arche uninstalled"; \
	else \
		echo "  arche is not installed via pipx"; \
	fi
