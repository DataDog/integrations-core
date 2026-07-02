# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest
import yaml

from ddev.ai.runtime.checkpoints import (
    CheckpointManager,
    CheckpointReadError,
    FailedCheckpoint,
    SuccessCheckpoint,
)

from .helpers import make_failed_checkpoint, make_success_checkpoint


@pytest.fixture
def manager(tmp_path: Path) -> CheckpointManager:
    return CheckpointManager(tmp_path / "checkpoints.yaml")


# ---------------------------------------------------------------------------
# read
# ---------------------------------------------------------------------------


def test_read_returns_empty_when_file_absent(manager: CheckpointManager):
    assert manager.read() == {}


def test_read_returns_empty_when_file_is_empty(manager: CheckpointManager):
    manager._path.write_text("")
    assert manager.read() == {}


def test_read_malformed_yaml_raises_checkpoint_read_error(manager: CheckpointManager):
    manager._path.write_text(": :\n -[")
    with pytest.raises(CheckpointReadError, match="checkpoints.yaml"):
        manager.read()


def test_read_unreadable_file_raises_checkpoint_read_error(manager: CheckpointManager, monkeypatch: pytest.MonkeyPatch):
    manager.write_phase_checkpoint("phase1", make_success_checkpoint())
    monkeypatch.setattr("pathlib.Path.read_text", lambda *_, **__: (_ for _ in ()).throw(OSError("permission denied")))
    with pytest.raises(CheckpointReadError, match="checkpoints.yaml"):
        manager.read()


def test_read_returns_validated_checkpoint(manager: CheckpointManager):
    manager.write_phase_checkpoint("phase1", make_success_checkpoint())
    data = manager.read()
    assert isinstance(data["phase1"], SuccessCheckpoint)


# ---------------------------------------------------------------------------
# write_phase_checkpoint
# ---------------------------------------------------------------------------


def test_write_and_read_back(manager: CheckpointManager):
    manager.write_phase_checkpoint("phase1", make_success_checkpoint())
    data = manager.read()
    assert isinstance(data["phase1"], SuccessCheckpoint)
    assert data["phase1"].tokens.total_input == 10
    assert data["phase1"].tokens.total_output == 20


def test_write_preserves_phase_data(manager: CheckpointManager):
    manager.write_phase_checkpoint(
        "phase1", make_success_checkpoint(phase_data={"endpoint_url": "http://localhost:8080"})
    )
    data = manager.read()
    assert isinstance(data["phase1"], SuccessCheckpoint)
    assert data["phase1"].phase_data["endpoint_url"] == "http://localhost:8080"


def test_write_creates_parent_dirs(tmp_path: Path):
    manager = CheckpointManager(tmp_path / "nested" / "dir" / "checkpoints.yaml")
    manager.write_phase_checkpoint("p", make_success_checkpoint())
    assert isinstance(manager.read()["p"], SuccessCheckpoint)


def test_write_multiple_phases(manager: CheckpointManager):
    manager.write_phase_checkpoint("phase1", make_success_checkpoint())
    manager.write_phase_checkpoint("phase2", make_failed_checkpoint())
    data = manager.read()
    assert isinstance(data["phase1"], SuccessCheckpoint)
    assert isinstance(data["phase2"], FailedCheckpoint)


def test_write_overwrites_existing_phase(manager: CheckpointManager):
    manager.write_phase_checkpoint("phase1", make_failed_checkpoint())
    manager.write_phase_checkpoint("phase1", make_success_checkpoint())
    assert isinstance(manager.read()["phase1"], SuccessCheckpoint)


# ---------------------------------------------------------------------------
# build_memory_prompt
# ---------------------------------------------------------------------------


def test_build_memory_prompt_no_additions(manager: CheckpointManager):
    result = manager.build_memory_prompt(None)
    assert result == "Write a brief summary of what you accomplished in this phase."


def test_build_memory_prompt_with_additions(manager: CheckpointManager):
    result = manager.build_memory_prompt("Also list the files you created.")
    assert result.startswith("Also list the files you created.")
    assert "Write a brief summary" in result


# ---------------------------------------------------------------------------
# write_memory / memory_content / memory_path
# ---------------------------------------------------------------------------


def test_write_memory_and_read_back(manager: CheckpointManager):
    manager.write_memory("draft", "Created integration.py and tests.")
    assert manager.memory_content("draft") == "Created integration.py and tests."


def test_write_memory_overwrites(manager: CheckpointManager):
    manager.write_memory("draft", "first version")
    manager.write_memory("draft", "second version")
    assert manager.memory_content("draft") == "second version"


def test_memory_content_absent_returns_placeholder(manager: CheckpointManager):
    assert manager.memory_content("nonexistent") == "<MEMORY NOT FOUND: nonexistent>"


def test_memory_path_returns_absolute_path(manager: CheckpointManager):
    path = manager.memory_path("phase1")
    assert isinstance(path, Path)
    assert path.is_absolute()
    assert path.name == "phase1_memory.md"


def test_memory_path_before_write(manager: CheckpointManager):
    path = manager.memory_path("phase1")
    assert not path.exists()


def test_memory_file_location(manager: CheckpointManager):
    manager.write_memory("phase1", "content")
    expected_path = manager._path.parent / "phase1_memory.md"
    assert expected_path.exists()
    assert expected_path.read_text() == "content"
    assert manager.memory_path("phase1") == expected_path.resolve()


# ---------------------------------------------------------------------------
# resolve_template_variable
# ---------------------------------------------------------------------------


def test_resolve_template_variable_memory_suffix(manager: CheckpointManager):
    manager.write_memory("draft", "Draft memory content.")
    assert manager.resolve_template_variable("draft_memory") == "Draft memory content."


def test_resolve_template_variable_non_memory_key(manager: CheckpointManager):
    assert manager.resolve_template_variable("some_variable") == "<VARIABLE UNDEFINED: some_variable>"


# ---------------------------------------------------------------------------
# successful_phases
# ---------------------------------------------------------------------------


def test_successful_phases_empty_when_no_file(manager: CheckpointManager):
    assert manager.successful_phases() == set()


def test_successful_phases_returns_only_succeeded(manager: CheckpointManager):
    manager.write_phase_checkpoint("a", make_success_checkpoint())
    manager.write_phase_checkpoint("b", make_failed_checkpoint())
    manager.write_phase_checkpoint("c", make_success_checkpoint())
    assert manager.successful_phases() == {"a", "c"}


def test_read_raises_on_invalid_checkpoint_entry(manager: CheckpointManager):
    manager.write_phase_checkpoint("a", make_success_checkpoint())
    raw = yaml.safe_load(manager._path.read_text())
    raw["b"] = "not-a-dict"
    manager._path.write_text(yaml.dump(raw))
    with pytest.raises(CheckpointReadError, match="phase 'b'"):
        manager.read()
