"""Project scanner: scan files and generate storage/archi.md via LLM."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from core.track_manager import STORAGE_DIR, load_project
from core.router import call_llm, get_model_for_phase

console = Console()

GLOBAL_ARCHI_PATH = STORAGE_DIR / "archi.md"

# Directories to ignore completely
SKIP_DIRS = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".venv", "venv", "env", ".env",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", ".tox",
    "dist", "build", ".next", ".nuxt", ".output", "target",
    "storage", ".idea", ".vscode", ".DS_Store",
    "coverage", ".coverage", "htmlcov",
}

# File extensions to skip (binary / generated / lock)
SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".class", ".o", ".so", ".dll", ".exe",
    ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3", ".wav", ".ogg",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".rar",
    ".lock", ".sum", ".resolved",
    ".min.js", ".min.css", ".map",
    ".db", ".sqlite", ".sqlite3",
}

# Files always included first, in this order
PRIORITY_FILES = [
    "README.md", "README.rst", "README.txt",
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "package-lock.json",
    "Cargo.toml", "go.mod",
    "pom.xml", "build.gradle",
    "Makefile", "makefile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".env.sample",
    "requirements.txt", "requirements-dev.txt", "requirements-prod.txt",
    "tsconfig.json", "vite.config.ts", "vite.config.js",
    "next.config.js", "nuxt.config.ts",
]

SCAN_PROMPT = """\
You are a senior software architect. Analyse the project structure and source files below.

Generate a concise, dense `archi.md` document that a developer can read in 30 seconds to \
understand the full technical picture before writing code. Include:

- **Stack** — languages, frameworks, main libraries and their versions (from config files)
- **Structure** — what each top-level directory contains
- **Entry points** — how the app starts / is invoked
- **Key modules / layers** — main components and their responsibilities
- **Patterns & conventions** — naming, file layout, coding style observed
- **Data flow** — how data enters, is processed, and exits (if discernible)
- **External services** — databases, APIs, cloud services referenced
- **Configuration** — env vars, config files, feature flags

Rules:
- Only write what you can actually observe in the provided files
- Be dense and factual, no filler
- Use Markdown headers (##) and bullet points
- Target ~500 words

Project: {name}
Stack declared: {stack}

--- DIRECTORY TREE ---
{tree}

--- KEY FILES ---
{files_content}
--- END ---

Output only the Markdown content, starting with # Architecture — {name}"""


def _build_tree(root: Path, max_depth: int = 4) -> str:
    """Build a compact directory tree string."""
    lines: list[str] = []

    def walk(path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return
        entries = [
            e for e in entries
            if e.name not in SKIP_DIRS and not e.name.startswith(".")
        ]
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{connector}{entry.name}{suffix}")
            if entry.is_dir():
                extension = "    " if is_last else "│   "
                walk(entry, prefix + extension, depth + 1)

    lines.append(f"{root.name}/")
    walk(root, "", 1)
    return "\n".join(lines)


def _collect_files(root: Path, max_chars: int = 50_000) -> str:
    """Read key files and return a combined string for the LLM."""
    parts: list[str] = []
    total = 0
    included: set[Path] = set()

    def add_file(p: Path, char_limit: int) -> None:
        nonlocal total
        if not p.exists() or not p.is_file():
            return
        if p in included:
            return
        if p.suffix in SKIP_EXTENSIONS:
            return
        try:
            content = p.read_text(errors="replace")
            snippet = content[:char_limit]
            if len(content) > char_limit:
                snippet += f"\n… (truncated, {len(content)} chars total)"
            parts.append(f"### {p.relative_to(root)}\n```\n{snippet}\n```")
            total += len(snippet)
            included.add(p)
        except Exception:
            pass

    # Priority files first (higher char budget)
    for fname in PRIORITY_FILES:
        if total >= max_chars:
            break
        add_file(root / fname, 6000)

    # Source files: walk the tree
    for p in sorted(root.rglob("*")):
        if total >= max_chars:
            break
        if not p.is_file():
            continue
        if p in included:
            continue
        # Skip noise directories
        if any(part in SKIP_DIRS or part.startswith(".") for part in p.relative_to(root).parts):
            continue
        if p.suffix in SKIP_EXTENSIONS:
            continue
        if p.stat().st_size > 60_000:
            continue
        add_file(p, 2500)

    return "\n\n".join(parts)


def get_global_archi() -> str:
    """Return the global archi.md content if it exists."""
    return GLOBAL_ARCHI_PATH.read_text() if GLOBAL_ARCHI_PATH.exists() else ""


def run_scan() -> None:
    """Scan the project and write storage/archi.md via LLM (review model)."""
    project = load_project()
    name = project.get("name", Path.cwd().name)
    stack = project.get("stack", "unknown")
    model = get_model_for_phase("review")

    console.print(f"\n[bold cyan]arche scan[/bold cyan] — Project analysis\n")
    console.print(f"[dim]Project :[/dim] {name}")
    console.print(f"[dim]Stack   :[/dim] {stack}")
    console.print(f"[dim]Model   :[/dim] {model}")

    root = Path.cwd()

    console.print("\n[dim]Building directory tree…[/dim]")
    tree = _build_tree(root)

    console.print("[dim]Collecting source files…[/dim]")
    files_content = _collect_files(root)
    file_count = files_content.count("### ")
    console.print(f"[dim]  → {file_count} files collected ({len(files_content):,} chars)[/dim]\n")

    prompt = SCAN_PROMPT.format(
        name=name,
        stack=stack,
        tree=tree,
        files_content=files_content,
    )

    console.print(Panel(
        f"Analysing with [bold]{model}[/bold]…\n"
        f"[dim]This may take 30–60 seconds on large projects.[/dim]",
        border_style="cyan",
    ))

    output = call_llm(prompt, phase="review", stream=True)

    STORAGE_DIR.mkdir(exist_ok=True)
    GLOBAL_ARCHI_PATH.write_text(output.strip() + "\n")

    console.print(f"\n[green]✓ archi.md written → {GLOBAL_ARCHI_PATH}[/green]")
    console.print("[dim]It will be automatically included in every 'arche task run' context.[/dim]")
