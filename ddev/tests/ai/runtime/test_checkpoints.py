# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest
import yaml

from ddev.ai.runtime.checkpoints import (
    CheckpointManager,
    CheckpointReadError,
    CheckpointStatus,
    CheckpointTokenInfo,
    FailedCheckpoint,
    SuccessCheckpoint,
)

from .conftest import FINISHED, make_failed, make_success


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
    with pytest.raises(CheckpointReadError, match="checkpoints.yaml"):
        manager.read()


def test_read_unreadable_file_raises_checkpoint_read_error(manager, monkeypatch):
    manager.write_phase_checkpoint("phase1", make_success())
    monkeypatch.setattr("pathlib.Path.read_text", lambda *_, **__: (_ for _ in ()).throw(OSError("permission denied")))
    with pytest.raises(CheckpointReadError, match="checkpoints.yaml"):
        manager.read()


def test_read_returns_validated_checkpoint(manager):
    manager.write_phase_checkpoint("phase1", make_success())
    data = manager.read()
    assert isinstance(data["phase1"], SuccessCheckpoint)
    assert data["phase1"].status == CheckpointStatus.SUCCESS


# ---------------------------------------------------------------------------
# write_phase_checkpoint
# ---------------------------------------------------------------------------


def test_write_and_read_back(manager):
    manager.write_phase_checkpoint("phase1", make_success())
    data = manager.read()
    assert data["phase1"].status == CheckpointStatus.SUCCESS
    assert data["phase1"].tokens.total_input == 10
    assert data["phase1"].tokens.total_output == 20


def test_write_preserves_extra_fields(manager):
    manager.write_phase_checkpoint("phase1", make_success(endpoint_url="http://localhost:8080"))
    data = manager.read()
    assert isinstance(data["phase1"], SuccessCheckpoint)
    assert data["phase1"].model_extra["endpoint_url"] == "http://localhost:8080"


def test_write_creates_parent_dirs(tmp_path):
    manager = CheckpointManager(tmp_path / "nested" / "dir" / "checkpoints.yaml")
    manager.write_phase_checkpoint("p", make_success())
    assert manager.read()["p"].status == CheckpointStatus.SUCCESS


def test_write_multiple_phases(manager):
    manager.write_phase_checkpoint("phase1", make_success())
    manager.write_phase_checkpoint("phase2", make_failed())
    data = manager.read()
    assert data["phase1"].status == CheckpointStatus.SUCCESS
    assert data["phase2"].status == CheckpointStatus.FAILED


def test_write_overwrites_existing_phase(manager):
    manager.write_phase_checkpoint("phase1", make_failed())
    manager.write_phase_checkpoint("phase1", make_success())
    assert manager.read()["phase1"].status == CheckpointStatus.SUCCESS


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
# write_memory / memory_content / memory_path
# ---------------------------------------------------------------------------


def test_write_memory_and_read_back(manager):
    manager.write_memory("draft", "Created integration.py and tests.")
    assert manager.memory_content("draft") == "Created integration.py and tests."


def test_write_memory_overwrites(manager):
    manager.write_memory("draft", "first version")
    manager.write_memory("draft", "second version")
    assert manager.memory_content("draft") == "second version"


def test_memory_content_absent_returns_placeholder(manager):
    assert manager.memory_content("nonexistent") == "<MEMORY NOT FOUND: nonexistent>"


def test_memory_path_returns_absolute_path(manager):
    path = manager.memory_path("phase1")
    assert isinstance(path, Path)
    assert path.is_absolute()
    assert path.name == "phase1_memory.md"


def test_memory_path_before_write(manager):
    path = manager.memory_path("phase1")
    assert not path.exists()


def test_memory_file_location(manager):
    manager.write_memory("phase1", "content")
    expected_path = manager._path.parent / "phase1_memory.md"
    assert expected_path.exists()
    assert expected_path.read_text() == "content"
    assert manager.memory_path("phase1") == expected_path.resolve()


# ---------------------------------------------------------------------------
# resolve_template_variable
# ---------------------------------------------------------------------------


def test_resolve_template_variable_memory_suffix(manager):
    manager.write_memory("draft", "Draft memory content.")
    assert manager.resolve_template_variable("draft_memory") == "Draft memory content."


def test_resolve_template_variable_non_memory_key(manager):
    assert manager.resolve_template_variable("some_variable") == "<VARIABLE UNDEFINED: some_variable>"


# ---------------------------------------------------------------------------
# successful_phases
# ---------------------------------------------------------------------------


def test_successful_phases_empty_when_no_file(manager):
    assert manager.successful_phases() == set()


def test_successful_phases_returns_only_succeeded(manager):
    manager.write_phase_checkpoint("a", make_success())
    manager.write_phase_checkpoint("b", make_failed())
    manager.write_phase_checkpoint("c", make_success())
    assert manager.successful_phases() == {"a", "c"}


def test_read_raises_on_invalid_checkpoint_entry(manager):
    manager.write_phase_checkpoint("a", make_success())
    raw = yaml.safe_load(manager._path.read_text())
    raw["b"] = "not-a-dict"
    manager._path.write_text(yaml.dump(raw))
    with pytest.raises(CheckpointReadError, match="phase 'b'"):
        manager.read()


# ---------------------------------------------------------------------------
# FailedCheckpoint fields
# ---------------------------------------------------------------------------


def test_failed_checkpoint_with_tokens(manager):
    cp = make_failed(tokens=CheckpointTokenInfo(total_input=5, total_output=15))
    manager.write_phase_checkpoint("phase1", cp)
    data = manager.read()
    assert isinstance(data["phase1"], FailedCheckpoint)
    assert data["phase1"].tokens is not None
    assert data["phase1"].tokens.total_input == 5


def test_failed_checkpoint_with_goal_validations(manager):
    cp = make_failed(goal_validations=[{"attempt": 1, "result": "fail"}])
    manager.write_phase_checkpoint("phase1", cp)
    data = manager.read()
    assert isinstance(data["phase1"], FailedCheckpoint)
    assert data["phase1"].goal_validations == [{"attempt": 1, "result": "fail"}]


def test_failed_checkpoint_started_at_none(manager):
    cp = FailedCheckpoint(
        status=CheckpointStatus.FAILED,
        started_at=None,
        finished_at=FINISHED,
        error="crashed before start",
    )
    manager.write_phase_checkpoint("phase1", cp)
    data = manager.read()
    assert data["phase1"].started_at is None
