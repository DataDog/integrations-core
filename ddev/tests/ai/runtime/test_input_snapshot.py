# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from ddev.ai.config.models import FlowInput, ResolvedFlow
from ddev.ai.runtime.input_snapshot import (
    CAPTURES_DIR_NAME,
    INPUTS_DIR_NAME,
    MANIFEST_NAME,
    pinned_snapshot_inputs,
    snapshot_path_inputs,
)


def make_flow(*inputs: FlowInput) -> ResolvedFlow:
    return ResolvedFlow(name="demo", agents={}, phases={}, flow=[], variables={}, inputs=list(inputs))


def snapshot_input(name: str = "prd") -> FlowInput:
    return FlowInput(name=name, label="Requirements", input_type="path", snapshot=True)


def write_source(tmp_path, text: str = "requirements"):
    source = tmp_path / "requirements.md"
    source.write_text(text, encoding="utf-8")
    return source


def capture_path(run_dir: Path, filename: str) -> Path:
    return run_dir / INPUTS_DIR_NAME / CAPTURES_DIR_NAME / filename


def test_copies_source_and_repoints_variable(tmp_path):
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"

    variables, captured = snapshot_path_inputs(make_flow(snapshot_input()), {"prd": str(source)}, run_dir)

    snapshot = capture_path(run_dir, "prd.md")
    assert variables == {"prd": str(snapshot)}
    assert snapshot.read_text(encoding="utf-8") == "requirements"
    assert [item.name for item in captured] == ["prd"]


def test_snapshot_is_read_only(tmp_path):
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"

    _variables, captured = snapshot_path_inputs(make_flow(snapshot_input()), {"prd": str(source)}, run_dir)

    assert captured[0].path.stat().st_mode & 0o222 == 0


def test_snapshot_survives_source_edits(tmp_path):
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"

    variables, _captured = snapshot_path_inputs(make_flow(snapshot_input()), {"prd": str(source)}, run_dir)
    source.write_text("rewritten", encoding="utf-8")

    assert Path(variables["prd"]).read_text(encoding="utf-8") == "requirements"


def test_manifest_records_provenance(tmp_path):
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"

    snapshot_path_inputs(make_flow(snapshot_input()), {"prd": str(source)}, run_dir)

    manifest = yaml.safe_load((run_dir / INPUTS_DIR_NAME / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["prd"]["source"] == str(source)
    assert manifest["prd"]["snapshot"] == "prd.md"
    assert manifest["prd"]["sha256"] == hashlib.sha256(b"requirements").hexdigest()
    assert manifest["prd"]["size"] == len("requirements")
    assert manifest["prd"]["captured_at"]


def test_resume_reuses_existing_snapshot(tmp_path):
    """A resume is handed the surviving copy and keeps it, whatever the source now holds."""
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"
    flow = make_flow(snapshot_input())
    launched, _captured = snapshot_path_inputs(flow, {"prd": str(source)}, run_dir)
    source.write_text("rewritten", encoding="utf-8")

    variables, captured = snapshot_path_inputs(flow, launched, run_dir, resume=True)

    snapshot = capture_path(run_dir, "prd.md")
    assert variables == {"prd": str(snapshot)}
    assert snapshot.read_text(encoding="utf-8") == "requirements"
    assert captured[0].source == source
    assert captured[0].diverged is True


def test_resume_reports_no_divergence_when_source_is_unchanged(tmp_path):
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"
    flow = make_flow(snapshot_input())
    launched, _captured = snapshot_path_inputs(flow, {"prd": str(source)}, run_dir)

    _variables, captured = snapshot_path_inputs(flow, launched, run_dir, resume=True)

    assert captured[0].diverged is False


def test_resume_reuses_snapshot_after_source_is_deleted(tmp_path):
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"
    flow = make_flow(snapshot_input())
    launched, _captured = snapshot_path_inputs(flow, {"prd": str(source)}, run_dir)
    source.unlink()

    variables, captured = snapshot_path_inputs(flow, launched, run_dir, resume=True)

    assert Path(variables["prd"]).read_text(encoding="utf-8") == "requirements"
    assert captured[0].diverged is True


def test_relaunch_recaptures_source(tmp_path):
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"
    flow = make_flow(snapshot_input())
    snapshot_path_inputs(flow, {"prd": str(source)}, run_dir)
    source.write_text("rewritten", encoding="utf-8")

    _variables, captured = snapshot_path_inputs(flow, {"prd": str(source)}, run_dir)

    assert captured[0].path.read_text(encoding="utf-8") == "rewritten"
    assert captured[0].diverged is False


def test_flow_without_snapshot_inputs_is_untouched(tmp_path):
    run_dir = tmp_path / "run"
    flow = make_flow(FlowInput(name="integration", label="Integration", input_type="string"))

    variables, captured = snapshot_path_inputs(flow, {"integration": "kuma"}, run_dir)

    assert variables == {"integration": "kuma"}
    assert captured == []
    assert not (run_dir / INPUTS_DIR_NAME).exists()


def test_unsupplied_optional_snapshot_is_skipped(tmp_path):
    run_dir = tmp_path / "run"
    flow = make_flow(FlowInput(name="prd", label="Requirements", input_type="path", snapshot=True, required=False))

    variables, captured = snapshot_path_inputs(flow, {}, run_dir)

    assert variables == {}
    assert captured == []
    assert not (run_dir / INPUTS_DIR_NAME).exists()


def test_pinned_snapshot_inputs_reports_the_surviving_copy(tmp_path):
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"
    snapshot_path_inputs(make_flow(snapshot_input()), {"prd": str(source)}, run_dir)

    pinned = pinned_snapshot_inputs(run_dir)

    assert pinned["prd"].source == source
    assert pinned["prd"].path == capture_path(run_dir, "prd.md")
    assert pinned["prd"].captured_at


def test_pinned_snapshot_inputs_omits_a_missing_copy(tmp_path):
    """A snapshot whose copy is gone must be collected again rather than reused."""
    source = write_source(tmp_path)
    run_dir = tmp_path / "run"
    snapshot_path_inputs(make_flow(snapshot_input()), {"prd": str(source)}, run_dir)
    capture_path(run_dir, "prd.md").unlink()

    assert pinned_snapshot_inputs(run_dir) == {}
