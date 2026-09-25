# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest

from ddev.ai.runtime.helpers import atomic_write_text


def test_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "dir" / "file.txt"

    atomic_write_text(target, "content")

    assert target.read_text(encoding="utf-8") == "content"


def test_overwrites_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("old content", encoding="utf-8")

    atomic_write_text(target, "new content")

    assert target.read_text(encoding="utf-8") == "new content"


def test_round_trips_non_ascii_content(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    text = "café résumé — 日本語テキスト"

    atomic_write_text(target, text)

    assert target.read_text(encoding="utf-8") == text


def test_failure_during_replace_leaves_no_tmp_residue_and_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "file.txt"
    target.write_text("original content", encoding="utf-8")

    def failing_replace(self: Path, destination: Path) -> Path:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "replace", failing_replace)

    with pytest.raises(OSError, match="disk full"):
        atomic_write_text(target, "new content")

    assert target.read_text(encoding="utf-8") == "original content"
    assert list(tmp_path.glob(f".{target.name}.*.tmp")) == []
