"""
core/model_registry.py — ModelRegistry backed by models.yaml

Resolution:
  resolve("claude/sonnet") → {binary, id, batch_args, interactive_args,
                               model_flag, system_flag, tools_flag}
  resolve("claude-sonnet-4-6") → reverse-lookup for backward compat
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_YAML = Path(__file__).parent / "models_default.yaml"


class ModelRegistry:
    def __init__(self, data: dict):
        self._data = data  # raw parsed YAML

    # ------------------------------------------------------------------ load/save

    @classmethod
    def load(cls, storage_dir: Path | str | None = None, track_dir: Path | str | None = None) -> "ModelRegistry":
        """Load from track_dir/models.yaml, then storage_dir/models.yaml, fallback to bundled default."""
        for candidate_dir in filter(None, [track_dir, storage_dir]):
            candidate = Path(candidate_dir) / "models.yaml"
            if candidate.exists():
                with open(candidate) as f:
                    return cls(yaml.safe_load(f) or {})
        with open(_DEFAULT_YAML) as f:
            return cls(yaml.safe_load(f) or {})

    def save(self, storage_dir: Path | str) -> None:
        """Persist registry to <storage_dir>/models.yaml."""
        path = Path(storage_dir) / "models.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self._data, f, allow_unicode=True, sort_keys=False)

    # ------------------------------------------------------------------ queries

    def list_tools(self) -> list[str]:
        return list((self._data.get("tools") or {}).keys())

    def get_tool(self, alias: str) -> dict | None:
        return (self._data.get("tools") or {}).get(alias)

    def get_default_model(self, tool_alias: str) -> str | None:
        tool = self.get_tool(tool_alias)
        if not tool:
            return None
        return tool.get("default_model")

    def list_models(self, tool_alias: str) -> dict[str, dict]:
        """Return {model_alias: {id, description}} for a tool."""
        tool = self.get_tool(tool_alias)
        if not tool:
            return {}
        return tool.get("models") or {}

    # ------------------------------------------------------------------ resolve

    def resolve(self, spec: str) -> dict[str, Any] | None:
        """
        Resolve a model spec to a full config dict.

        Formats accepted:
          "claude/sonnet"          → tool_alias/model_alias  (new format)
          "claude-sonnet-4-6"      → raw model id            (backward compat)
          "claude"                 → tool_alias only, uses default_model
        """
        tools: dict = self._data.get("tools") or {}

        # --- new format: "tool/model_alias"
        if "/" in spec:
            tool_alias, model_alias = spec.split("/", 1)
            tool = tools.get(tool_alias)
            if not tool:
                return None
            models = tool.get("models") or {}
            model = models.get(model_alias)
            if not model:
                return None
            return self._build_resolved(tool, model)

        # --- tool alias only: use default_model
        if spec in tools:
            tool = tools[spec]
            default = tool.get("default_model")
            models = tool.get("models") or {}
            model = models.get(default) if default else None
            if model is None and models:
                model = next(iter(models.values()))
            if model is None:
                model = {"id": spec, "description": ""}
            return self._build_resolved(tool, model)

        # --- backward compat: raw model id string
        for tool_alias, tool in tools.items():
            models = tool.get("models") or {}
            for _alias, mdata in models.items():
                if mdata.get("id") == spec:
                    return self._build_resolved(tool, mdata)

        return None

    def _build_resolved(self, tool: dict, model: dict) -> dict[str, Any]:
        return {
            "binary": tool.get("binary", ""),
            "id": model.get("id", ""),
            "description": model.get("description", ""),
            "batch_args": list(tool.get("batch_args") or []),
            "interactive_args": list(tool.get("interactive_args") or []),
            "model_flag": tool.get("model_flag", ""),
            "system_flag": tool.get("system_flag", ""),
            "tools_flag": tool.get("tools_flag", ""),
            "file_support": tool.get("file_support", {"images": False}),
        }

    # ------------------------------------------------------------------ detection

    def detect_available(self) -> list[str]:
        """Return tool aliases whose binary is present in PATH."""
        available = []
        for alias, tool in (self._data.get("tools") or {}).items():
            binary = tool.get("binary", "")
            if binary and shutil.which(binary):
                available.append(alias)
        return available

    # ------------------------------------------------------------------ CRUD

    def add_tool(self, alias: str, config: dict) -> None:
        if "tools" not in self._data:
            self._data["tools"] = {}
        self._data["tools"][alias] = config

    def remove_tool(self, alias: str) -> bool:
        tools = self._data.get("tools") or {}
        if alias in tools:
            del tools[alias]
            return True
        return False

    def add_model(self, tool_alias: str, model_alias: str, model_id: str, description: str = "") -> bool:
        tool = self.get_tool(tool_alias)
        if not tool:
            return False
        if "models" not in tool:
            tool["models"] = {}
        tool["models"][model_alias] = {"id": model_id, "description": description}
        return True
