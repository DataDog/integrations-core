# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import os

import pytest

from ddev.ai.config.loading.discovery import discover
from ddev.ai.config.loading.files import FileError, MarkdownFile, YamlFile


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_recursive_walk_finds_nested_files(tmp_path):
    write(tmp_path / "a.md", "---\nname: a\n---\nbody")
    write(tmp_path / "nested" / "deep" / "b.yaml", "- x: 1\n")

    results = list(discover([tmp_path]))

    paths = {r.path for r in results}
    assert tmp_path / "a.md" in paths
    assert tmp_path / "nested" / "deep" / "b.yaml" in paths


def test_only_md_yaml_yml_are_candidates(tmp_path):
    write(tmp_path / "a.md", "---\nname: a\n---\nbody")
    write(tmp_path / "b.yaml", "- x: 1\n")
    write(tmp_path / "c.yml", "- y: 2\n")
    write(tmp_path / "d.txt", "ignored")
    write(tmp_path / "e.py", "ignored = True")

    results = list(discover([tmp_path]))

    paths = {r.path for r in results}
    assert paths == {tmp_path / "a.md", tmp_path / "b.yaml", tmp_path / "c.yml"}


def test_non_config_files_skipped(tmp_path):
    write(tmp_path / "plain.md", "no front matter")
    write(tmp_path / "scalar.yaml", "just_a_string")

    results = list(discover([tmp_path]))

    assert results == []


def test_broken_files_yielded_as_file_error(tmp_path):
    write(tmp_path / "broken.md", "---\nthis: : bad: [\n---\nbody")
    write(tmp_path / "broken.yaml", "this: : bad: [")

    results = list(discover([tmp_path]))

    assert len(results) == 2
    assert all(isinstance(r, FileError) for r in results)
    paths = {r.path for r in results}
    assert paths == {tmp_path / "broken.md", tmp_path / "broken.yaml"}


def test_invalid_utf8_yields_file_error(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_bytes(b"\xff")

    results = list(discover([tmp_path]))

    assert len(results) == 1
    assert isinstance(results[0], FileError)
    assert results[0].path == path
    assert "not valid UTF-8" in results[0].message


def test_results_sorted_by_path(tmp_path):
    write(tmp_path / "z.md", "---\nname: z\n---\nbody")
    write(tmp_path / "a.md", "---\nname: a\n---\nbody")
    write(tmp_path / "m.yaml", "- x: 1\n")

    results = list(discover([tmp_path]))

    result_paths = [r.path for r in results]
    assert result_paths == sorted(result_paths)


def test_directories_not_yielded(tmp_path):
    write(tmp_path / "sub" / "a.md", "---\nname: a\n---\nbody")

    results = list(discover([tmp_path]))

    assert all(r.path.is_file() for r in results)
    assert not any(isinstance(r, (MarkdownFile, YamlFile)) and r.path.is_dir() for r in results)


def test_same_directory_listed_twice_yields_each_file_once(tmp_path):
    write(tmp_path / "a.md", "---\nname: a\n---\nbody")

    results = list(discover([tmp_path, tmp_path]))

    assert [r.path for r in results] == [tmp_path / "a.md"]


def test_overlapping_directories_yield_each_file_once(tmp_path):
    write(tmp_path / "sub" / "a.md", "---\nname: a\n---\nbody")

    results = list(discover([tmp_path, tmp_path / "sub"]))

    assert [r.path for r in results] == [tmp_path / "sub" / "a.md"]


def test_symlinked_directory_alias_yields_each_file_once(tmp_path):
    real = tmp_path / "real"
    write(real / "a.md", "---\nname: a\n---\nbody")
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)

    results = list(discover([real, link]))

    assert len(results) == 1


def test_unreadable_directory_yields_file_error(tmp_path):
    if os.getuid() == 0:
        pytest.skip("root bypasses directory permissions")
    blocked = tmp_path / "blocked"
    write(blocked / "a.md", "---\nname: a\n---\nbody")
    blocked.chmod(0o000)
    try:
        results = list(discover([tmp_path]))
    finally:
        blocked.chmod(0o755)

    errors = [r for r in results if isinstance(r, FileError)]
    assert any(r.path == blocked for r in errors)


def test_non_overlapping_directories_are_all_walked(tmp_path):
    write(tmp_path / "one" / "a.md", "---\nname: a\n---\nbody")
    write(tmp_path / "two" / "b.md", "---\nname: b\n---\nbody")

    results = list(discover([tmp_path / "one", tmp_path / "two"]))

    assert {r.path for r in results} == {tmp_path / "one" / "a.md", tmp_path / "two" / "b.md"}
