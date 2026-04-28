# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.ai.tools.fs.file_registry import FileRegistry

OWNER_A = "agent-a"
OWNER_B = "agent-b"


@pytest.fixture
def registry() -> FileRegistry:
    return FileRegistry()


# ---------------------------------------------------------------------------
# is_known
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "record,expected",
    [
        (False, False),
        (True, True),
    ],
)
def test_is_known(registry: FileRegistry, tmp_path, record, expected) -> None:
    path = str(tmp_path / "file.txt")
    if record:
        registry.record(OWNER_A, path, "hello")
    assert registry.is_known(OWNER_A, path) is expected


def test_is_known_different_path(registry: FileRegistry, tmp_path) -> None:
    registry.record(OWNER_A, str(tmp_path / "other.txt"), "hello")
    assert registry.is_known(OWNER_A, str(tmp_path / "file.txt")) is False


def test_is_known_is_scoped_to_owner(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    registry.record(OWNER_A, path, "hello")
    assert registry.is_known(OWNER_A, path) is True
    assert registry.is_known(OWNER_B, path) is False


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "recorded_content,verify_content,expected",
    [
        ("hello", "hello", True),
        ("hello", "world", False),
        (None, "any content", False),
    ],
)
def test_verify(registry: FileRegistry, tmp_path, recorded_content, verify_content, expected) -> None:
    path = str(tmp_path / "file.txt")
    if recorded_content is not None:
        registry.record(OWNER_A, path, recorded_content)
    assert registry.verify(OWNER_A, path, verify_content) is expected


def test_verify_fails_for_different_agent(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    registry.record(OWNER_A, path, "hello")
    assert registry.verify(OWNER_B, path, "hello") is False


# ---------------------------------------------------------------------------
# record overwrites
# ---------------------------------------------------------------------------


def test_record_overwrites_previous_hash_within_agent(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    registry.record(OWNER_A, path, "old")
    registry.record(OWNER_A, path, "new")

    assert registry.verify(OWNER_A, path, "new") is True
    assert registry.verify(OWNER_A, path, "old") is False


def test_record_does_not_cross_agents(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    registry.record(OWNER_A, path, "from-a")
    registry.record(OWNER_B, path, "from-b")

    assert registry.verify(OWNER_A, path, "from-a") is True
    assert registry.verify(OWNER_A, path, "from-b") is False
    assert registry.verify(OWNER_B, path, "from-b") is True
    assert registry.verify(OWNER_B, path, "from-a") is False


# ---------------------------------------------------------------------------
# path normalization
# ---------------------------------------------------------------------------


def test_normalize_relative_and_absolute_are_same_key(registry: FileRegistry, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    abs_path = str(tmp_path / "file.txt")
    rel_path = "file.txt"

    registry.record(OWNER_A, abs_path, "hello")
    assert registry.is_known(OWNER_A, rel_path) is True
    assert registry.verify(OWNER_A, rel_path, "hello") is True


def test_normalize_tilde_and_absolute_are_same_key(registry: FileRegistry, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    tilde_path = "~/foo.txt"
    abs_path = str(tmp_path / "foo.txt")

    registry.record(OWNER_A, tilde_path, "hello")
    assert registry.is_known(OWNER_A, abs_path) is True
    assert registry.is_known(OWNER_A, tilde_path) is True
    assert registry.verify(OWNER_A, abs_path, "hello") is True


# ---------------------------------------------------------------------------
# lock_for — shared across agents so concurrent writes serialize on the path
# ---------------------------------------------------------------------------


def test_lock_for_same_path_returns_same_instance(registry: FileRegistry, tmp_path) -> None:
    path = str(tmp_path / "file.txt")
    assert registry.lock_for(path) is registry.lock_for(path)


def test_lock_for_different_paths_return_different_instances(registry: FileRegistry, tmp_path) -> None:
    path_a = str(tmp_path / "a.txt")
    path_b = str(tmp_path / "b.txt")
    assert registry.lock_for(path_a) is not registry.lock_for(path_b)


def test_lock_for_normalizes_path(registry: FileRegistry, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    abs_path = str(tmp_path / "file.txt")
    rel_path = "file.txt"
    assert registry.lock_for(abs_path) is registry.lock_for(rel_path)
