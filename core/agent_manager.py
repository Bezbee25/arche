from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

STORAGE_DIR = Path(".arche-storage")
AGENTS_DIR = STORAGE_DIR / "agents"


def _slugify(text: str) -> str:
    text = re.sub(r"[^\w\s/-]", "", text.lower())
    text = re.sub(r"[\s]+", "-", text.strip())
    return text[:64]


def _agent_dir(agent_id: str) -> Path:
    return AGENTS_DIR / agent_id


def _meta_path(agent_id: str) -> Path:
    return _agent_dir(agent_id) / "meta.yaml"


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def _serialize(agent: dict) -> dict:
    out = dict(agent)
    for key in ("created_at", "updated_at"):
        if isinstance(out.get(key), datetime):
            out[key] = out[key].isoformat()
    return out


def create_agent(
    name: str,
    role: str,
    description: str,
    system_prompt: str,
    model: Optional[str] = None,
) -> dict:
    agent_id = _slugify(name)
    if _agent_dir(agent_id).exists():
        agent_id = f"{agent_id}-{uuid.uuid4().hex[:6]}"

    now = datetime.now().isoformat()
    agent = {
        "id": agent_id,
        "name": name,
        "role": role,
        "description": description,
        "system_prompt": system_prompt,
        "model": model,
        "created_at": now,
        "updated_at": now,
    }
    _save_yaml(_meta_path(agent_id), agent)
    return agent


def get_agent(agent_id: str) -> Optional[dict]:
    path = _meta_path(agent_id)
    if not path.exists():
        if AGENTS_DIR.exists():
            for d in AGENTS_DIR.iterdir():
                if d.name.startswith(agent_id):
                    mp = d / "meta.yaml"
                    if mp.exists():
                        return _load_yaml(mp)
        return None
    return _load_yaml(path)


def list_agents() -> list[dict]:
    if not AGENTS_DIR.exists():
        return []
    agents = []
    for d in sorted(AGENTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        mp = d / "meta.yaml"
        if mp.exists():
            meta = _load_yaml(mp)
            if meta.get("id"):
                agents.append(meta)
    agents.sort(key=lambda a: a.get("created_at", ""))
    return agents


def update_agent(agent_id: str, **kwargs) -> Optional[dict]:
    agent = get_agent(agent_id)
    if not agent:
        return None
    allowed = {"name", "role", "description", "system_prompt", "model"}
    for key, value in kwargs.items():
        if key in allowed and value is not None:
            agent[key] = value
    agent["updated_at"] = datetime.now().isoformat()
    _save_yaml(_meta_path(agent["id"]), agent)
    return agent


def delete_agent(agent_id: str) -> bool:
    agent = get_agent(agent_id)
    if not agent:
        return False
    import shutil
    shutil.rmtree(_agent_dir(agent["id"]), ignore_errors=True)
    return True


_SENIOR_DEVELOPER_PROMPT = """\
You are a senior software engineer with 10+ years of production experience. You approach every task with the following principles:

## Code Quality
- Write clean, self-documenting code. Names must reveal intent; avoid abbreviations.
- Keep functions small and focused (single responsibility). Prefer composition over inheritance.
- Eliminate dead code, commented-out blocks, and TODO stubs before committing.
- Apply DRY judiciously — three occurrences before abstracting, not two.

## Architecture
- Design for the current requirement, not hypothetical futures. Avoid over-engineering.
- Prefer simple, boring solutions. Complexity must be justified by a concrete constraint.
- Draw clear boundaries between layers (presentation / domain / infrastructure).
- Make dependencies explicit; avoid hidden coupling via global state or singletons.
- Consider failure modes from the start: retries, circuit breakers, graceful degradation.

## Testing
- Write tests before or alongside implementation, not after.
- Unit tests cover pure logic; integration tests cover boundaries (DB, APIs, queues).
- A test that doesn't fail when the code is broken is worthless — assert the right thing.
- Aim for high coverage on critical paths, not 100% everywhere.
- Test names describe behavior: `test_user_cannot_login_with_expired_token`.

## Security
- Never trust user input — validate at every system boundary.
- Parameterize all queries; never build SQL/HTML/shell commands via string concatenation.
- Store secrets in environment variables or a secrets manager, never in code or VCS.
- Apply least-privilege: each component gets only the permissions it needs.
- Log security-relevant events (auth failures, privilege escalations) but never log credentials or PII.

## Performance
- Profile before optimizing. Measure, don't guess.
- Cache at the right layer with an explicit invalidation strategy.
- Prefer async I/O for network-bound work; avoid blocking the event loop.
- Be aware of N+1 queries; use eager loading or batch fetches where needed.

## Code Review
- Review for correctness first, style second.
- Ask questions rather than making accusations: "What happens if X is null here?"
- Approve code that is good enough and ships value — perfect is the enemy of done.
- Leave the codebase better than you found it, but scope changes to the task at hand.

## Documentation
- Document the *why*, not the *what*. The code shows what; comments explain decisions and trade-offs.
- Keep docs close to the code (ADRs, inline comments on non-obvious logic).
- Update docs when the code changes — stale docs are worse than no docs.

## Communication
- Raise blockers early. Ask for clarification before building the wrong thing.
- Provide concrete alternatives when rejecting an approach.
- Estimate with confidence intervals, not false precision.
"""

_DEFAULT_AGENTS: list[dict] = [
    {
        "name": "Senior Developer",
        "role": "developer",
        "description": (
            "A senior software engineer covering code quality, architecture, "
            "testing, security, performance, and code review best practices."
        ),
        "system_prompt": _SENIOR_DEVELOPER_PROMPT,
        "model": None,
    },
]


def seed_default_agents() -> None:
    if list_agents():
        return
    for spec in _DEFAULT_AGENTS:
        create_agent(**spec)
