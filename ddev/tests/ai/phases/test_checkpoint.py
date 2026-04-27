# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.phases.checkpoint import CheckpointManager, CheckpointReadError


@pytest.fixture
def manager(tmp_path) -> CheckpointManager:
    return CheckpointManager(tmp_path / "checkpoints.yaml")


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


def test_read_returns_empty_when_file_absent(manager):
    assert manager.read() == {}


def test_read_returns_empty_when_file_is_empty(manager):
    manager._path.write_text("")
    assert manager.read() == {}


def test_read_malformed_yaml_raises_checkpoint_read_error(manager):
    manager._path.write_text(": :\n -[")
    with pytest.raises(CheckpointReadError, match=str(manager._path)):
        manager.read()


def test_read_unreadable_file_raises_checkpoint_read_error(manager, monkeypatch):
    manager._path.write_text("phase1:\n  status: success\n")
    monkeypatch.setattr("pathlib.Path.read_text", lambda *_: (_ for _ in ()).throw(OSError("permission denied")))
    with pytest.raises(CheckpointReadError, match=str(manager._path)):
        manager.read()


# ---------------------------------------------------------------------------
# write_phase_checkpoint
# ---------------------------------------------------------------------------


def test_write_and_read_back(manager):
    manager.write_phase_checkpoint("phase1", {"status": "success", "tokens": 100})
    data = manager.read()
    assert data["phase1"]["status"] == "success"
    assert data["phase1"]["tokens"] == 100


def test_write_creates_parent_dirs(tmp_path):
    manager = CheckpointManager(tmp_path / "nested" / "dir" / "checkpoints.yaml")
    manager.write_phase_checkpoint("p", {"status": "success"})
    assert manager.read()["p"]["status"] == "success"


def test_write_multiple_phases(manager):
    manager.write_phase_checkpoint("phase1", {"status": "success"})
    manager.write_phase_checkpoint("phase2", {"status": "failed"})
    data = manager.read()
    assert data["phase1"]["status"] == "success"
    assert data["phase2"]["status"] == "failed"


def test_write_overwrites_existing_phase(manager):
    manager.write_phase_checkpoint("phase1", {"status": "running"})
    manager.write_phase_checkpoint("phase1", {"status": "success"})
    assert manager.read()["phase1"]["status"] == "success"


# ---------------------------------------------------------------------------
# build_memory_prompt
# ---------------------------------------------------------------------------


def test_build_memory_prompt_no_additions(manager):
    result = manager.build_memory_prompt(None)
    assert result == "Write a brief summary of what you accomplished in this phase."


def test_build_memory_prompt_with_additions(manager):
    result = manager.build_memory_prompt("Also list the files you created.")
    assert result.startswith("Also list the files you created.")
    assert "Write a brief summary" in result


# ---------------------------------------------------------------------------
# write_memory / get_memory
# ---------------------------------------------------------------------------


def test_write_memory_and_read_back(manager):
    manager.write_phase_checkpoint("p", {})  # ensure parent dir exists
    manager.write_memory("draft", "Created integration.py and tests.")
    assert manager.get_memory("draft") == "Created integration.py and tests."


def test_write_memory_overwrites(manager):
    manager.write_phase_checkpoint("p", {})
    manager.write_memory("draft", "first version")
    manager.write_memory("draft", "second version")
    assert manager.get_memory("draft") == "second version"


def test_get_memory_absent_returns_placeholder(manager):
    assert manager.get_memory("nonexistent") == "<MEMORY NOT FOUND: nonexistent>"


def test_memory_file_location(manager):
    manager.write_phase_checkpoint("p", {})
    manager.write_memory("phase1", "content")
    expected_path = manager._path.parent / "phase1_memory.md"
    assert expected_path.exists()
    assert expected_path.read_text() == "content"
