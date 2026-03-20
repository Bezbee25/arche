from __future__ import annotations

from typing import Optional

import requests


class JiraClient:
    def __init__(self, url: str, login: str, api_key: str) -> None:
        self._base = url.rstrip("/")
        self._auth = (login, api_key)
        self._headers = {"Accept": "application/json"}

    @classmethod
    def from_settings(cls) -> "JiraClient":
        from core.track_manager import load_jira_settings

        settings = load_jira_settings()
        return cls(
            url=settings["url"],
            login=settings["login"],
            api_key=settings["api_key"],
        )

    def _get(self, path: str) -> dict:
        endpoint = f"{self._base}{path}"
        try:
            response = requests.get(
                endpoint,
                auth=self._auth,
                headers=self._headers,
                timeout=15,
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise RuntimeError("Request timed out after 15 seconds") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(str(exc)) from exc

        if response.status_code == 401:
            raise RuntimeError("Authentication failed — check login and API key")
        if response.status_code == 403:
            raise RuntimeError("Access forbidden — account may lack permissions")
        if response.status_code == 404:
            raise RuntimeError(f"Resource not found: {path}")
        if not response.ok:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")

        return response.json()

    def get_epic(self, epic_key: str) -> dict:
        key = epic_key.strip().upper()
        data = self._get(f"/rest/api/2/issue/{key}?fields=summary,description,issuetype")
        fields: dict = data.get("fields", {})
        raw_description = fields.get("description") or ""
        return {
            "key": key,
            "summary": fields.get("summary") or "",
            "description": _extract_text(raw_description),
        }

    def validate_jql(self, jql: str) -> dict:
        safe_jql = jql.strip()
        if not safe_jql:
            return {"ok": False, "error": "JQL query is empty"}
        try:
            data = self._get(
                f"/rest/api/2/search?jql={requests.utils.quote(safe_jql)}"
                "&fields=summary&maxResults=5&validateQuery=strict"
            )
        except RuntimeError as exc:
            return {"ok": False, "error": str(exc)}

        total: int = data.get("total", 0)
        previews: list[str] = [
            (issue.get("fields") or {}).get("summary") or issue.get("key", "")
            for issue in data.get("issues", [])
        ]
        return {"ok": True, "total": total, "preview": previews}

    def fetch_issues_by_jql(self, jql: str, max_results: int = 50) -> list[dict]:
        safe_jql = jql.strip()
        if not safe_jql:
            return []
        page_size = min(max_results, 100)
        collected: list[dict] = []
        start_at = 0
        while len(collected) < max_results:
            remaining = max_results - len(collected)
            batch_size = min(page_size, remaining)
            data = self._get(
                f"/rest/api/2/search?jql={requests.utils.quote(safe_jql)}"
                f"&fields=summary,description&maxResults={batch_size}&startAt={start_at}"
            )
            issues = data.get("issues") or []
            for issue in issues:
                fields: dict = issue.get("fields") or {}
                collected.append(
                    {
                        "key": issue.get("key", ""),
                        "summary": fields.get("summary") or "",
                        "description": _extract_text(fields.get("description") or ""),
                    }
                )
            total: int = data.get("total", 0)
            start_at += len(issues)
            if not issues or start_at >= total:
                break
        return collected

    def get_epic_children(self, epic_key: str) -> list[dict]:
        return self.get_child_issues(epic_key)

    def get_child_issues(self, epic_key: str) -> list[dict]:
        key = epic_key.strip().upper()
        jql = f'"Epic Link" = {key} OR "parent" = {key}'
        data = self._get(
            f"/rest/api/2/search?jql={requests.utils.quote(jql)}"
            "&fields=summary,description,status&maxResults=100"
        )
        issues = data.get("issues", [])
        return [
            {
                "key": issue.get("key", ""),
                "summary": (issue.get("fields") or {}).get("summary") or "",
                "description": _extract_text(
                    (issue.get("fields") or {}).get("description") or ""
                ),
                "status": (
                    ((issue.get("fields") or {}).get("status") or {}).get("name") or ""
                ),
            }
            for issue in issues
        ]


def _extract_text(description: object) -> str:
    if not description:
        return ""
    if isinstance(description, str):
        return description
    if isinstance(description, dict):
        return _adf_to_text(description)
    return ""


def _adf_to_text(node: dict) -> str:
    parts: list[str] = []
    if node.get("type") == "text":
        parts.append(node.get("text") or "")
    for child in node.get("content") or []:
        parts.append(_adf_to_text(child))
    sep = "\n" if node.get("type") in ("paragraph", "heading", "bulletList", "listItem") else ""
    return sep.join(p for p in parts if p)


def validate_connection(url: str, login: str, api_key: str) -> dict:
    base = url.rstrip("/")
    endpoint = f"{base}/rest/api/2/myself"
    try:
        response = requests.get(
            endpoint,
            auth=(login, api_key),
            headers={"Accept": "application/json"},
            timeout=10,
        )
    except requests.exceptions.ConnectionError as exc:
        return {"ok": False, "error": f"Connection failed: {exc}"}
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "Connection timed out after 10 seconds"}
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "error": str(exc)}

    if response.status_code == 200:
        data = response.json()
        display_name: Optional[str] = data.get("displayName")
        return {"ok": True, "display_name": display_name}

    if response.status_code == 401:
        return {"ok": False, "error": "Authentication failed — check login and API key"}
    if response.status_code == 403:
        return {"ok": False, "error": "Access forbidden — account may lack permissions"}
    if response.status_code == 404:
        return {"ok": False, "error": "Jira URL not found — check the base URL"}

    return {"ok": False, "error": f"Unexpected HTTP {response.status_code}"}
