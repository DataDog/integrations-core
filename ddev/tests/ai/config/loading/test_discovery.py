# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

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
