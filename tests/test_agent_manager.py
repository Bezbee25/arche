import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import core.agent_manager as am


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(am, "STORAGE_DIR", tmp_path / ".arche-storage")
    monkeypatch.setattr(am, "AGENTS_DIR", tmp_path / ".arche-storage" / "agents")
    am.AGENTS_DIR.mkdir(parents=True, exist_ok=True)


# --- create_agent ---

def test_create_agent_returns_dict_with_all_fields():
    agent = am.create_agent("My Agent", "developer", "desc", "prompt")
    assert agent["id"] == "my-agent"
    assert agent["name"] == "My Agent"
    assert agent["role"] == "developer"
    assert agent["description"] == "desc"
    assert agent["system_prompt"] == "prompt"
    assert agent["model"] is None
    assert "created_at" in agent
    assert "updated_at" in agent


def test_create_agent_with_model():
    agent = am.create_agent("Bot", "reviewer", "d", "p", model="claude-sonnet")
    assert agent["model"] == "claude-sonnet"


def test_create_agent_persists_to_disk():
    am.create_agent("Disk Agent", "dev", "d", "p")
    meta = am.AGENTS_DIR / "disk-agent" / "meta.yaml"
    assert meta.exists()


def test_create_agent_slug_collision_appends_suffix():
    am.create_agent("Alpha", "dev", "d", "p")
    agent2 = am.create_agent("Alpha", "qa", "d2", "p2")
    assert agent2["id"] != "alpha"
    assert agent2["id"].startswith("alpha-")


# --- get_agent ---

def test_get_agent_by_exact_id():
    created = am.create_agent("Exact", "dev", "d", "p")
    fetched = am.get_agent(created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]


def test_get_agent_by_prefix():
    am.create_agent("Prefix Match", "dev", "d", "p")
    # "prefix" is a prefix of "prefix-match"
    fetched = am.get_agent("prefix")
    assert fetched is not None
    assert fetched["name"] == "Prefix Match"


def test_get_agent_returns_none_for_unknown():
    assert am.get_agent("nonexistent-agent") is None


# --- list_agents ---

def test_list_agents_empty():
    assert am.list_agents() == []


def test_list_agents_returns_all():
    am.create_agent("A", "dev", "d", "p")
    am.create_agent("B", "qa", "d", "p")
    agents = am.list_agents()
    assert len(agents) == 2


def test_list_agents_sorted_by_created_at():
    am.create_agent("First", "dev", "d", "p")
    am.create_agent("Second", "dev", "d", "p")
    agents = am.list_agents()
    assert agents[0]["created_at"] <= agents[1]["created_at"]


# --- update_agent ---

def test_update_agent_modifies_allowed_fields():
    created = am.create_agent("Update Me", "dev", "d", "old prompt")
    updated = am.update_agent(created["id"], system_prompt="new prompt", role="reviewer")
    assert updated["system_prompt"] == "new prompt"
    assert updated["role"] == "reviewer"


def test_update_agent_bumps_updated_at():
    import time
    created = am.create_agent("Time Agent", "dev", "d", "p")
    old_ts = created["updated_at"]
    time.sleep(0.01)
    updated = am.update_agent(created["id"], description="new desc")
    assert updated["updated_at"] >= old_ts


def test_update_agent_ignores_disallowed_fields():
    created = am.create_agent("Guard", "dev", "d", "p")
    original_id = created["id"]
    am.update_agent(created["id"], id="hacked", created_at="2000-01-01")
    fetched = am.get_agent(original_id)
    assert fetched["id"] == original_id


def test_update_agent_returns_none_for_unknown():
    assert am.update_agent("no-such-agent", name="x") is None


def test_update_agent_persists_to_disk():
    created = am.create_agent("Persist Update", "dev", "d", "p")
    am.update_agent(created["id"], description="updated desc")
    fetched = am.get_agent(created["id"])
    assert fetched["description"] == "updated desc"


# --- delete_agent ---

def test_delete_agent_returns_true_and_removes_dir():
    created = am.create_agent("To Delete", "dev", "d", "p")
    agent_dir = am.AGENTS_DIR / created["id"]
    assert agent_dir.exists()
    result = am.delete_agent(created["id"])
    assert result is True
    assert not agent_dir.exists()


def test_delete_agent_returns_false_for_unknown():
    assert am.delete_agent("ghost-agent") is False


def test_delete_agent_removes_from_list():
    created = am.create_agent("Gone", "dev", "d", "p")
    am.delete_agent(created["id"])
    assert am.list_agents() == []


# --- seed_default_agents ---

def test_seed_default_agents_creates_senior_developer():
    am.seed_default_agents()
    agents = am.list_agents()
    assert len(agents) == 1
    assert agents[0]["id"] == "senior-developer"
    assert agents[0]["role"] == "developer"


def test_seed_default_agents_is_idempotent():
    am.seed_default_agents()
    am.seed_default_agents()
    agents = am.list_agents()
    assert len(agents) == 1


def test_seed_default_agents_noop_when_agents_exist():
    am.create_agent("Existing", "qa", "d", "p")
    am.seed_default_agents()
    agents = am.list_agents()
    assert len(agents) == 1
    assert agents[0]["name"] == "Existing"


# --- edge cases ---

def test_create_agent_with_special_chars_in_name():
    agent = am.create_agent("My Agent #1!", "dev", "d", "p")
    assert agent["id"]
    assert "/" not in agent["id"]


def test_create_agent_name_truncated_at_64():
    long_name = "a" * 100
    agent = am.create_agent(long_name, "dev", "d", "p")
    assert len(agent["id"]) <= 64
