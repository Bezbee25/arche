from __future__ import annotations

from typing import Optional

import requests


class JiraClient:
    def __init__(self, url: str, login: str, api_key: str) -> None:
        self._base = url.rstrip("/")
        self._auth = (login, api_key)
        self._headers = {"Accept": "application/json", "Content-Type": "application/json"}

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
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")

        return response.json()

    def _post(self, path: str, body: dict) -> dict:
        endpoint = f"{self._base}{path}"
        try:
            response = requests.post(
                endpoint,
                auth=self._auth,
                headers=self._headers,
                json=body,
                timeout=15,
            )
        except requests.exceptions.ConnectionError as exc:
            raise RuntimeError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout:
            raise RuntimeError("Request timed out after 15 seconds")
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(str(exc)) from exc

        if response.status_code == 401:
            raise RuntimeError("Authentication failed — check login and API key")
        if response.status_code == 403:
            raise RuntimeError("Access forbidden — account may lack permissions")
        if not response.ok:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")

        return response.json()

    def _search(self, jql: str, fields: list[str], max_results: int = 50, next_page_token: str | None = None) -> dict:
        """POST /rest/api/3/search/jql (Jira Cloud v3)."""
        body: dict = {"jql": jql, "fields": fields, "maxResults": max_results}
        if next_page_token:
            body["nextPageToken"] = next_page_token
        return self._post("/rest/api/3/search/jql", body)

    def get_epic(self, epic_key: str) -> dict:
        key = epic_key.strip().upper()
        data = self._get(f"/rest/api/3/issue/{key}?fields=summary,description,issuetype")
        fields: dict = data.get("fields", {})
        return {
            "key": key,
            "summary": fields.get("summary") or "",
            "description": _extract_text(fields.get("description") or ""),
        }

    def validate_jql(self, jql: str) -> dict:
        safe_jql = jql.strip()
        if not safe_jql:
            return {"ok": False, "error": "JQL query is empty"}
        try:
            data = self._search(safe_jql, fields=["summary"], max_results=10)
        except RuntimeError as exc:
            return {"ok": False, "error": str(exc)}

        issues = data.get("issues", [])
        has_more = bool(data.get("nextPageToken"))
        # v3 API no longer returns total — derive from page + nextPageToken
        total: int = data.get("total") or len(issues)
        if has_more and total == len(issues):
            total = -1  # unknown, more than page size
        previews: list[str] = [
            (issue.get("fields") or {}).get("summary") or issue.get("key", "")
            for issue in issues
        ]
        return {"ok": True, "total": total, "has_more": has_more, "preview": previews}

    def fetch_issues_by_jql(self, jql: str, max_results: int = 50) -> list[dict]:
        safe_jql = jql.strip()
        if not safe_jql:
            return []
        page_size = min(max_results, 100)
        collected: list[dict] = []
        next_page_token: str | None = None
        while len(collected) < max_results:
            remaining = max_results - len(collected)
            batch_size = min(page_size, remaining)
            data = self._search(
                safe_jql,
                fields=["summary", "description"],
                max_results=batch_size,
                next_page_token=next_page_token,
            )
            issues = data.get("issues") or []
            for issue in issues:
                f: dict = issue.get("fields") or {}
                collected.append({
                    "key": issue.get("key", ""),
                    "summary": f.get("summary") or "",
                    "description": _extract_text(f.get("description") or ""),
                })
            next_page_token = data.get("nextPageToken")
            if not issues or not next_page_token:
                break
        return collected

    def get_epic_children(self, epic_key: str) -> list[dict]:
        return self.get_child_issues(epic_key)

    def get_child_issues(self, epic_key: str) -> list[dict]:
        key = epic_key.strip().upper()
        try:
            data = self._search(f'"Epic Link" = {key} OR parent = {key}', fields=["summary", "description", "status"], max_results=100)
        except RuntimeError:
            data = self._search(f"parent = {key}", fields=["summary", "description", "status"], max_results=100)
        issues = data.get("issues", [])
        return [
            {
                "key": issue.get("key", ""),
                "summary": (issue.get("fields") or {}).get("summary") or "",
                "description": _extract_text((issue.get("fields") or {}).get("description") or ""),
                "status": (((issue.get("fields") or {}).get("status") or {}).get("name") or ""),
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
    endpoint = f"{base}/rest/api/3/myself"
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
