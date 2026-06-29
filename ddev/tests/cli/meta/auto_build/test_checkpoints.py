# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ddev.cli.meta.auto_build.checkpoints import (
    CHECKPOINTS_DIR,
    CHECKPOINTS_FILE,
    Checkpoints,
    PhaseCheckpoint,
    PhaseStatus,
    load_checkpoints,
    save_checkpoint,
)


def make_checkpoint(
    phase: int = 0, status: PhaseStatus = PhaseStatus.SUCCESS, data: dict | None = None
) -> PhaseCheckpoint:
    return PhaseCheckpoint(
        phase=phase,
        status=status,
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        data=data or {},
    )


def checkpoints_path(directory: Path) -> Path:
    return directory / CHECKPOINTS_DIR / CHECKPOINTS_FILE


class TestSaveCheckpoint:
    def test_creates_directory_and_file(self, tmp_path: Path):
        checkpoint = make_checkpoint()
        save_checkpoint(tmp_path, checkpoint)

        assert checkpoints_path(tmp_path).exists()

    def test_file_contains_saved_checkpoint(self, tmp_path: Path):
        checkpoint = make_checkpoint(phase=0, status=PhaseStatus.SUCCESS, data={"key": "value"})
        save_checkpoint(tmp_path, checkpoint)

        with checkpoints_path(tmp_path).open() as f:
            raw = yaml.safe_load(f)

        assert len(raw) == 1
        assert raw[0]["phase"] == 0
        assert raw[0]["status"] == "success"
        assert raw[0]["data"] == {"key": "value"}

    def test_appends_multiple_checkpoints(self, tmp_path: Path):
        save_checkpoint(tmp_path, make_checkpoint(phase=0))
        save_checkpoint(tmp_path, make_checkpoint(phase=1, status=PhaseStatus.FAILED))

        with checkpoints_path(tmp_path).open() as f:
            raw = yaml.safe_load(f)

        assert len(raw) == 2
        assert raw[0]["phase"] == 0
        assert raw[1]["phase"] == 1
        assert raw[1]["status"] == "failed"


class TestLoadCheckpoints:
    def test_returns_empty_when_file_missing(self, tmp_path: Path):
        result = load_checkpoints(tmp_path)

        assert result == Checkpoints(checkpoints=[])

    def test_parses_existing_file(self, tmp_path: Path):
        checkpoints_path(tmp_path).parent.mkdir(parents=True)
        raw = [{"phase": 0, "status": "success", "timestamp": "2026-01-01T00:00:00+00:00", "data": {}}]
        with checkpoints_path(tmp_path).open("w") as f:
            yaml.dump(raw, f)

        result = load_checkpoints(tmp_path)

        assert len(result.checkpoints) == 1
        assert result.checkpoints[0].phase == 0
        assert result.checkpoints[0].status == PhaseStatus.SUCCESS

    def test_raises_on_invalid_schema(self, tmp_path: Path):
        checkpoints_path(tmp_path).parent.mkdir(parents=True)
        raw = [{"phase": "not_an_int", "status": "invalid_status", "timestamp": "bad_date", "data": {}}]
        with checkpoints_path(tmp_path).open("w") as f:
            yaml.dump(raw, f)

        with pytest.raises(ValidationError):
            load_checkpoints(tmp_path)


class TestRoundtrip:
    def test_save_then_load_preserves_data(self, tmp_path: Path):
        checkpoint = make_checkpoint(phase=2, status=PhaseStatus.INTERRUPTED, data={"metrics": ["cpu", "mem"]})
        save_checkpoint(tmp_path, checkpoint)

        result = load_checkpoints(tmp_path)

        assert len(result.checkpoints) == 1
        loaded = result.checkpoints[0]
        assert loaded.phase == checkpoint.phase
        assert loaded.status == checkpoint.status
        assert loaded.data == checkpoint.data
