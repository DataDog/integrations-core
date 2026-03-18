# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.ai.tools.fs.file_registry import FileRegistry


@pytest.fixture
def registry() -> FileRegistry:
    return FileRegistry()


# ---------------------------------------------------------------------------
# is_known
# ---------------------------------------------------------------------------


def test_unknown_path_not_known(registry: FileRegistry, tmp_path) -> None:
    assert registry.is_known(str(tmp_path / "file.txt")) is False


def test_record_makes_path_known(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    registry.record(path, "hello")
    assert registry.is_known(path) is True


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def test_verify_matches_recorded_content(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    registry.record(path, "hello")
    assert registry.verify(path, "hello") is True


def test_verify_fails_for_changed_content(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    registry.record(path, "hello")
    assert registry.verify(path, "world") is False


def test_verify_fails_for_unknown_path(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    assert registry.verify(path, "any content") is False


# ---------------------------------------------------------------------------
# record overwrites
# ---------------------------------------------------------------------------


def test_record_overwrites_previous_hash(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    registry.record(path, "old")
    registry.record(path, "new")

    assert registry.verify(path, "new") is True
    assert registry.verify(path, "old") is False


# ---------------------------------------------------------------------------
# path normalization
# ---------------------------------------------------------------------------


def test_normalize_relative_and_absolute_are_same_key(registry: FileRegistry, tmp_path, monkeypatch) -> None:
    # Make tmp_path the cwd so that a relative path resolves to the same absolute path
    monkeypatch.chdir(tmp_path)

    abs_path = str(tmp_path / "file.txt")
    rel_path = "file.txt"

    registry.record(abs_path, "hello")
    assert registry.is_known(rel_path) is True
    assert registry.verify(rel_path, "hello") is True


# ---------------------------------------------------------------------------
# get_lock
# ---------------------------------------------------------------------------


def test_get_lock_same_path_returns_same_instance(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    assert registry.get_lock(path) is registry.get_lock(path)


def test_get_lock_different_paths_return_different_instances(registry: FileRegistry, tmp_path) -> None:
    path_a = str(tmp_path / "a.txt")
    path_b = str(tmp_path / "b.txt")
    assert registry.get_lock(path_a) is not registry.get_lock(path_b)


def test_get_lock_normalizes_path(registry: FileRegistry, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    abs_path = str(tmp_path / "file.txt")
    rel_path = "file.txt"
    assert registry.get_lock(abs_path) is registry.get_lock(rel_path)
