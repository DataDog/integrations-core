# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import yaml

from ddev.ai.phases.checkpoint import CheckpointManager, CheckpointValidationError, validate_checkpoint_output

# ---------------------------------------------------------------------------
# CheckpointManager.read
# ---------------------------------------------------------------------------


def test_read_returns_empty_dict_when_file_missing(tmp_path):
    mgr = CheckpointManager(tmp_path / "checkpoints.yaml")
    assert mgr.read() == {}


def test_read_returns_contents_of_existing_file(tmp_path):
    path = tmp_path / "checkpoints.yaml"
    path.write_text(yaml.dump({"phase_1": {"status": "success", "count": 3}}))
    mgr = CheckpointManager(path)
    assert mgr.read() == {"phase_1": {"status": "success", "count": 3}}


def test_read_returns_empty_dict_for_empty_file(tmp_path):
    path = tmp_path / "checkpoints.yaml"
    path.write_text("")
    mgr = CheckpointManager(path)
    assert mgr.read() == {}


# ---------------------------------------------------------------------------
# CheckpointManager.write_phase
# ---------------------------------------------------------------------------


def test_write_phase_creates_file_when_missing(tmp_path):
    path = tmp_path / "sub" / "checkpoints.yaml"
    mgr = CheckpointManager(path)
    assert not path.exists()
    mgr.write_phase("phase_1", {"status": "success"})
    assert path.exists()


def test_write_phase_stores_data_under_phase_name(tmp_path):
    path = tmp_path / "checkpoints.yaml"
    mgr = CheckpointManager(path)
    mgr.write_phase("analyze", {"items": 5, "status": "success"})
    data = yaml.safe_load(path.read_text())
    assert data["analyze"] == {"items": 5, "status": "success"}


def test_write_phase_accumulates_without_overwriting_other_phases(tmp_path):
    path = tmp_path / "checkpoints.yaml"
    mgr = CheckpointManager(path)
    mgr.write_phase("phase_1", {"status": "success", "count": 3})
    mgr.write_phase("phase_2", {"status": "success", "result": "ok"})
    data = yaml.safe_load(path.read_text())
    assert "phase_1" in data
    assert "phase_2" in data
    assert data["phase_1"] == {"status": "success", "count": 3}
    assert data["phase_2"] == {"status": "success", "result": "ok"}


def test_write_phase_overwrites_existing_section_for_same_phase(tmp_path):
    path = tmp_path / "checkpoints.yaml"
    mgr = CheckpointManager(path)
    mgr.write_phase("phase_1", {"status": "failed", "error": "oops"})
    mgr.write_phase("phase_1", {"status": "success", "count": 3})
    data = yaml.safe_load(path.read_text())
    assert data["phase_1"]["status"] == "success"
    assert "error" not in data["phase_1"]


# ---------------------------------------------------------------------------
# CheckpointManager.as_yaml_string
# ---------------------------------------------------------------------------


def test_as_yaml_string_returns_placeholder_when_empty(tmp_path):
    mgr = CheckpointManager(tmp_path / "checkpoints.yaml")
    assert mgr.as_yaml_string() == "(no checkpoints yet)"


def test_as_yaml_string_returns_yaml_when_data_exists(tmp_path):
    path = tmp_path / "checkpoints.yaml"
    mgr = CheckpointManager(path)
    mgr.write_phase("phase_1", {"status": "success"})
    result = mgr.as_yaml_string()
    assert "phase_1" in result
    assert "success" in result


# ---------------------------------------------------------------------------
# validate_checkpoint_output
# ---------------------------------------------------------------------------


def test_valid_yaml_with_matching_schema_returns_parsed_dict():
    raw = "items: 3\nstatus: done"
    result = validate_checkpoint_output(raw, {"items": 0, "status": ""})
    assert result == {"items": 3, "status": "done"}


def test_empty_schema_accepts_any_mapping():
    raw = "anything: goes\nfoo: bar"
    result = validate_checkpoint_output(raw, {})
    assert result["anything"] == "goes"


def test_extra_keys_beyond_schema_are_allowed():
    raw = "required_key: value\nextra_key: bonus"
    result = validate_checkpoint_output(raw, {"required_key": ""})
    assert "extra_key" in result


def test_invalid_yaml_raises_checkpoint_validation_error():
    with pytest.raises(CheckpointValidationError, match="not valid YAML"):
        validate_checkpoint_output(": : invalid : :", {"key": ""})


def test_non_mapping_yaml_raises_checkpoint_validation_error():
    with pytest.raises(CheckpointValidationError, match="mapping"):
        validate_checkpoint_output("- item1\n- item2", {"key": ""})


def test_plain_string_raises_checkpoint_validation_error():
    with pytest.raises(CheckpointValidationError, match="mapping"):
        validate_checkpoint_output("just a string", {"key": ""})


def test_missing_schema_key_raises_checkpoint_validation_error():
    raw = "present_key: value"
    with pytest.raises(CheckpointValidationError, match="missing_key"):
        validate_checkpoint_output(raw, {"present_key": "", "missing_key": ""})


def test_null_response_raises_checkpoint_validation_error():
    """An agent returning only whitespace or empty string produces None from yaml.safe_load."""
    with pytest.raises(CheckpointValidationError, match="mapping"):
        validate_checkpoint_output("", {"key": ""})
