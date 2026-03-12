"""LLM Router: dispatch to the right model/CLI based on phase."""
from __future__ import annotations

import shutil
import subprocess
from typing import Optional

from core.track_manager import load_project, STORAGE_DIR
from core.model_registry import ModelRegistry

# Default model assignments per phase (new tool/alias format)
DEFAULT_MODELS = {
    "spec":   "claude/opus",
    "think":  "claude/opus",
    "plan":   "claude/sonnet",
    "arch":   "claude/sonnet",
    "dev":    "claude/sonnet",
    "debug":  "claude/sonnet",
    "doc":    "gemini/flash",
    "review": "claude/sonnet",
}

# Tools granted to claude per phase
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

# Fallback resolved config when registry is unavailable
_FALLBACK_RESOLVED = {
    "binary":          "claude",
    "id":              "claude-sonnet-4-6",
    "batch_args":      ["-p", "--dangerously-skip-permissions"],
    "interactive_args": [],
    "model_flag":      "--model",
    "system_flag":     "--system-prompt",
    "tools_flag":      "--allowedTools",
}


def _get_registry(track_meta: Optional[dict] = None) -> ModelRegistry:
    track_dir = None
    if track_meta and track_meta.get("id"):
        from core.track_manager import TRACKS_DIR
        track_dir = TRACKS_DIR / track_meta["id"]
    return ModelRegistry.load(STORAGE_DIR, track_dir=track_dir)


def detect_available_clis() -> list[str]:
    """Return tool aliases whose binary is present in PATH."""
    try:
        return _get_registry().detect_available()
    except Exception:
        available = []
        for cli in ["claude", "gemini", "codex", "vibe"]:
            if shutil.which(cli):
                available.append(cli)
        if shutil.which("copilot"):
            available.append("copilot")
        return available


def get_model_for_phase(phase: str, track_meta: Optional[dict] = None) -> str:
    """Return model spec for phase. Lookup: track meta → project.yaml → defaults."""
    if track_meta and "models" in track_meta:
        model = track_meta["models"].get(phase)
        if model:
            return model
    project = load_project()
    if "models" in project:
        model = project["models"].get(phase)
        if model:
            return model
    return DEFAULT_MODELS.get(phase, "claude/sonnet")


def get_tools_for_phase(phase: str, track_meta: Optional[dict] = None) -> list[str]:
    """Return the list of tools to grant the CLI for a given phase."""
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


def _resolve_model_spec(spec: str, track_meta: Optional[dict] = None) -> dict:
    """Resolve a model spec string to a full config dict via registry."""
    try:
        registry = _get_registry(track_meta)
        resolved = registry.resolve(spec)
        if resolved:
            return resolved
    except Exception:
        pass
    # Fallback: try to infer binary from spec prefix
    result = dict(_FALLBACK_RESOLVED)
    if spec.startswith("gemini"):
        result.update({"binary": "gemini", "id": spec,
                        "batch_args": ["-y"], "interactive_args": ["-y"],
                        "model_flag": "--model", "system_flag": "", "tools_flag": ""})
    elif spec.startswith("copilot"):
        result.update({"binary": "copilot", "id": spec,
                        "batch_args": ["-p"],
                        "interactive_args": [],
                        "model_flag": "--model", "system_flag": "", "tools_flag": ""})
    elif not spec.startswith("claude"):
        result["id"] = spec
    else:
        result["id"] = spec
    return result


def _get_cli_for_model(model: str) -> str:
    """Return CLI binary name for a model spec. Backward-compat helper."""
    resolved = _resolve_model_spec(model)
    return resolved.get("binary", "claude")


def _build_cmd_from_resolved(
    resolved: dict,
    system: Optional[str],
    allowed_tools: list[str],
    interactive: bool = False,
) -> list[str]:
    """Build a CLI command list from a resolved model config."""
    binary = resolved["binary"]
    args = resolved["interactive_args"] if interactive else resolved["batch_args"]
    cmd = [binary] + list(args)

    model_flag = resolved.get("model_flag", "")
    model_id = resolved.get("id", "")
    if model_flag and model_id:
        cmd += [model_flag, model_id]

    system_flag = resolved.get("system_flag", "")
    if system_flag and system:
        cmd += [system_flag, system]

    tools_flag = resolved.get("tools_flag", "")
    if tools_flag and allowed_tools:
        cmd += [tools_flag, ",".join(allowed_tools)]

    return cmd


def _build_command(
    cli: str,
    model: str,
    system: Optional[str],
    allowed_tools: list[str],
) -> list[str]:
    """Build the CLI command for batch (stdin pipe) mode.

    Backward-compat wrapper used by server.py. Resolves config via registry
    when possible, falls back to hardcoded behaviour.
    """
    resolved = _resolve_for_binary(cli, model)
    return _build_cmd_from_resolved(resolved, system, allowed_tools, interactive=False)


def _build_interactive_command(
    cli: str,
    model: str,
    system: Optional[str],
    allowed_tools: list[str],
) -> list[str]:
    """Build the CLI command for interactive PTY use."""
    resolved = _resolve_for_binary(cli, model)
    return _build_cmd_from_resolved(resolved, system, allowed_tools, interactive=True)


def _resolve_for_binary(cli: str, model: str) -> dict:
    """Find tool config by binary name and inject model id.

    `cli` may be either a tool alias (e.g. "copilot") or a binary name
    (e.g. "gh").  We match on both to handle either call convention.
    """
    try:
        registry = _get_registry()
        # Find tool whose alias or binary matches cli
        for alias in registry.list_tools():
            tool = registry.get_tool(alias)
            if tool and (tool.get("binary") == cli or alias == cli):
                # If model is a spec like "claude/haiku", resolve it to get the real id
                if "/" in model:
                    full = registry.resolve(model)
                    if full:
                        return full
                    # spec tool/alias not found, extract alias part as fallback
                    _, model_alias = model.split("/", 1)
                    models = tool.get("models") or {}
                    mdata = models.get(model_alias, {"id": model_alias, "description": ""})
                else:
                    mdata = {"id": model, "description": ""}
                from core.model_registry import ModelRegistry as _MR
                dummy = _MR.__new__(_MR)
                dummy._data = registry._data
                resolved = dummy._build_resolved(tool, mdata)
                return resolved
    except Exception:
        pass
    # Hard fallback per binary
    return _hardcoded_resolved(cli, model)


def _hardcoded_resolved(cli: str, model: str) -> dict:
    """Minimal fallback resolved dict when registry is not available."""
    if cli == "claude":
        return {
            "binary": "claude", "id": model,
            "batch_args": ["-p", "--dangerously-skip-permissions"],
            "interactive_args": [],
            "model_flag": "--model", "system_flag": "--system-prompt",
            "tools_flag": "--allowedTools",
        }
    if cli == "gemini":
        return {
            "binary": "gemini", "id": model,
            "batch_args": ["-y"], "interactive_args": ["-y"],
            "model_flag": "--model", "system_flag": "", "tools_flag": "",
        }
    if cli == "codex":
        return {
            "binary": "codex", "id": model,
            "batch_args": ["-q"], "interactive_args": [],
            "model_flag": "", "system_flag": "", "tools_flag": "",
        }
    if cli == "vibe":
        return {
            "binary": "vibe", "id": model,
            "batch_args": ["-p"], "interactive_args": [],
            "model_flag": "", "system_flag": "", "tools_flag": "",
        }
    if cli in ("copilot", "gh"):
        return {
            "binary": "copilot", "id": model,
            "batch_args": ["-p"],
            "interactive_args": [],
            "model_flag": "--model", "system_flag": "", "tools_flag": "",
        }
    # unknown CLI — pass model via stdin with no flags
    return {
        "binary": cli, "id": model,
        "batch_args": [], "interactive_args": [],
        "model_flag": "", "system_flag": "", "tools_flag": "",
    }


def call_llm(
    prompt: str,
    phase: str,
    track_meta: Optional[dict] = None,
    system: Optional[str] = None,
    stream: bool = True,
    tools: Optional[list[str]] = None,
) -> str:
    """Call the appropriate LLM CLI with the given prompt.

    `tools` overrides the default tool list for the phase (claude only).
    Returns the full output as a string.
    """
    spec = get_model_for_phase(phase, track_meta)
    resolved = _resolve_model_spec(spec, track_meta)
    cli = resolved["binary"]

    if not shutil.which(cli):
        # Fallback to claude if available
        if cli != "claude" and shutil.which("claude"):
            resolved = _resolve_model_spec("claude/sonnet", track_meta)
            cli = "claude"
        else:
            raise RuntimeError(
                f"CLI '{cli}' not found. Install it or configure a different model for phase '{phase}'."
            )

    allowed_tools = tools if tools is not None else get_tools_for_phase(phase, track_meta)
    cmd = _build_cmd_from_resolved(resolved, system, allowed_tools)

    print(f"[router] cmd: {' '.join(cmd)}", flush=True)

    try:
        if stream:
            return _run_streaming(cmd, prompt)
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"LLM call failed: {e.stderr}") from e


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
