"""LLM Router: dispatch to the right model/CLI based on phase."""
from __future__ import annotations

import shutil
import subprocess
from typing import Optional

from core.track_manager import load_project

# Default model assignments per phase
DEFAULT_MODELS = {
    "spec": "claude-opus-4-6",
    "think": "claude-opus-4-6",
    "plan": "claude-sonnet-4-6",
    "arch": "claude-sonnet-4-6",
    "dev": "claude-sonnet-4-6",
    "debug": "claude-sonnet-4-6",
    "doc": "gemini-2.0-flash",
    "review": "claude-haiku-4-5-20251001",
}

# Tools granted to claude per phase
# Phases that produce/modify files need Write + Edit + Bash
DEFAULT_TOOLS: dict[str, list[str]] = {
    "spec":   ["Read"],
    "think":  ["Read"],
    "plan":   ["Read"],
    "arch":   ["Read"],
    "dev":    ["Read", "Write", "Edit", "Bash"],
    "debug":  ["Read", "Write", "Edit", "Bash"],
    "doc":    ["Read", "Write", "Edit"],
    "review": ["Read"],
}

# Map model prefix → CLI binary
MODEL_CLI = {
    "claude": "claude",
    "gemini": "gemini",
    "codex":  "codex",
    "gpt":    "codex",
    "vibe":   "vibe",
    "devstral": "vibe",
}


def detect_available_clis() -> list[str]:
    available = []
    for cli in ["claude", "gemini", "codex", "vibe"]:
        if shutil.which(cli):
            available.append(cli)
    return available


def get_model_for_phase(phase: str, track_meta: Optional[dict] = None) -> str:
    if track_meta and "models" in track_meta:
        model = track_meta["models"].get(phase)
        if model:
            return model
    project = load_project()
    if "models" in project:
        model = project["models"].get(phase)
        if model:
            return model
    return DEFAULT_MODELS.get(phase, "claude-sonnet-4-6")


def get_tools_for_phase(phase: str, track_meta: Optional[dict] = None) -> list[str]:
    """Return the list of tools to grant the CLI for a given phase.

    Lookup order: plan override → project config → built-in defaults.
    """
    if track_meta and "tools" in track_meta:
        tools = track_meta["tools"].get(phase)
        if tools:
            return tools
    project = load_project()
    if "tools" in project:
        tools = project["tools"].get(phase)
        if tools:
            return tools
    return DEFAULT_TOOLS.get(phase, ["Read", "Write", "Edit", "Bash"])


def _get_cli_for_model(model: str) -> str:
    for prefix, cli in MODEL_CLI.items():
        if model.startswith(prefix):
            return cli
    return "claude"


def call_llm(
    prompt: str,
    phase: str,
    track_meta: Optional[dict] = None,
    system: Optional[str] = None,
    stream: bool = True,
    tools: Optional[list[str]] = None,
) -> str:
    """Call the appropriate LLM CLI with the given prompt.

    `tools`  overrides the default tool list for the phase (claude only).
    Returns the full output as a string.
    """
    model = get_model_for_phase(phase, track_meta)
    cli = _get_cli_for_model(model)

    if not shutil.which(cli):
        if cli != "claude" and shutil.which("claude"):
            cli = "claude"
            model = "claude-sonnet-4-6"
        else:
            raise RuntimeError(
                f"CLI '{cli}' not found. Install it or configure a different model for phase '{phase}'."
            )

    allowed_tools = tools if tools is not None else get_tools_for_phase(phase, track_meta)
    cmd = _build_command(cli, model, system, allowed_tools)

    try:
        if stream:
            return _run_streaming(cmd, prompt)
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"LLM call failed: {e.stderr}") from e


def _build_command(
    cli: str,
    model: str,
    system: Optional[str],
    allowed_tools: list[str],
) -> list[str]:
    """Build the CLI command. Prompt is passed via stdin, not as an argument."""
    if cli == "claude":
        # --dangerously-skip-permissions is required for non-interactive (batch) mode:
        # without it, Claude Code blocks file writes waiting for user confirmation,
        # which hangs forever since stdin is a pipe.
        # Access restrictions are enforced via protected_paths in the prompt instead.
        cmd = ["claude", "-p", "--dangerously-skip-permissions", "--model", model]
        if system:
            cmd += ["--system-prompt", system]
        if allowed_tools:
            cmd += ["--allowedTools", ",".join(allowed_tools)]
        return cmd

    elif cli == "gemini":
        return ["gemini", "--model", model, "-y"]

    elif cli == "codex":
        return ["codex", "-q"]

    elif cli == "vibe":
        return ["vibe", "-p"]

    return ["claude", "-p"]


def _build_interactive_command(
    cli: str,
    model: str,
    system: Optional[str],
    allowed_tools: list[str],
) -> list[str]:
    """Build the CLI command for interactive PTY use (no batch/print flags).

    The resulting command is meant to run in a real terminal where the user
    can interact with the LLM if it asks questions.
    """
    if cli == "claude":
        cmd = ["claude", "--model", model]
        if system:
            cmd += ["--system-prompt", system]
        if allowed_tools:
            cmd += ["--allowedTools", ",".join(allowed_tools)]
        return cmd

    elif cli == "gemini":
        return ["gemini", "--model", model, "-y"]

    elif cli == "codex":
        return ["codex"]

    elif cli == "vibe":
        return ["vibe"]

    return ["claude"]


def _run_streaming(cmd: list[str], prompt: str) -> str:
    """Run command with prompt on stdin, stream stdout, return full output."""
    output_lines = []
    with subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    ) as proc:
        # Write prompt to stdin then close it
        proc.stdin.write(prompt)
        proc.stdin.close()

        for line in proc.stdout:
            print(line, end="", flush=True)
            output_lines.append(line)
        proc.wait()
        if proc.returncode != 0:
            err = proc.stderr.read()
            raise subprocess.CalledProcessError(proc.returncode, cmd, stderr=err)
    return "".join(output_lines)
