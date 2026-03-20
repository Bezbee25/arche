from __future__ import annotations


_SYSTEM_PROMPT = (
    "You are a technical spec writer. Given a Jira Epic, produce a concise arche "
    "spec.md. Output ONLY the Markdown content — no preamble, no code fences, no commentary."
)

_PROMPT_TEMPLATE = """\
Convert this Jira Epic into a clean arche spec.md.

Epic summary: {summary}

Epic description:
{description}

Output exactly this structure (fill in real content, keep headings):

## Goal

<one clear sentence stating what this track achieves>

## Context

<2–4 sentences of background explaining why this exists and who benefits>

## Requirements

- <concrete requirement>
- <concrete requirement>
- <add as many as needed>
"""


def refine_epic_spec(summary: str, description: str) -> str:
    from core.router import call_llm

    prompt = _PROMPT_TEMPLATE.format(
        summary=summary or "(no summary)",
        description=description or "(no description provided)",
    )
    try:
        return call_llm(prompt, phase="plan", tools=[]).strip()
    except Exception:
        return _minimal_spec(summary, description)


def _minimal_spec(summary: str, description: str) -> str:
    parts = [f"## Goal\n\n{summary or '(no summary)'}"]
    if description:
        parts.append(f"## Context\n\n{description}")
    parts.append("## Requirements\n\n_(to be defined)_")
    return "\n\n".join(parts)


_TASK_SYSTEM_PROMPT = (
    "You are a senior developer writing task descriptions for a dev agent. "
    "Be concise, implementation-focused, and precise. "
    "Output ONLY the task description — no preamble, no code fences, no commentary."
)

_TASK_PROMPT_TEMPLATE = """\
Refine this Jira issue into a concise developer task description.

Issue summary: {summary}

Issue description:
{description}

Write 2–5 sentences covering:
1. What to implement (the concrete deliverable)
2. Why it matters (brief context or acceptance criteria)

Be specific about technical scope. Avoid restating the summary verbatim.
"""


def refine_task_description(summary: str, raw_description: str) -> str:
    from core.router import call_llm

    prompt = _TASK_PROMPT_TEMPLATE.format(
        summary=summary or "(no summary)",
        description=raw_description or "(no description provided)",
    )
    try:
        return call_llm(prompt, phase="plan", tools=[]).strip()
    except Exception:
        return _minimal_task_description(summary, raw_description)


def _minimal_task_description(summary: str, raw_description: str) -> str:
    if raw_description:
        return f"{summary}\n\n{raw_description}".strip()
    return summary or "(no description)"
