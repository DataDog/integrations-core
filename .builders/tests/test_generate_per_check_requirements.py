"""Tests for generate_per_check_requirements.py: enumeration and closure contents."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

generate_per_check_requirements = importlib.import_module('generate_per_check_requirements')

BASE_DEPS_GROUP = ['base-dep==1.0.0']
BASE_HTTP_GROUP = ['http-dep==2.0.0']


def _write_pyproject(repo: Path, directory: str, contents: str) -> None:
    path = repo / directory
    path.mkdir(parents=True)
    (path / 'pyproject.toml').write_text(contents, encoding='utf-8')


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / 'repo'
    repo.mkdir()
    _write_pyproject(
        repo,
        'datadog_checks_base',
        '[project]\nname = "datadog-checks-base"\nversion = "1.0"\n\n'
        '[project.optional-dependencies]\ndeps = ["base-dep==1.0.0"]\nhttp = ["http-dep==2.0.0"]\n',
    )
    _write_pyproject(
        repo,
        'postgres',
        '[project]\nname = "datadog-checks-postgres"\nversion = "1.0"\n\n'
        '[project.optional-dependencies]\ndeps = ["psycopg==3.3.4", "http-dep==2.0.0"]\n',
    )
    _write_pyproject(
        repo,
        'redisdb',
        '[project]\nname = "datadog-checks-redisdb"\nversion = "1.0"\n\n'
        '[project.optional-dependencies]\ndeps = []\n',
    )
    _write_pyproject(
        repo,
        'ddev',
        '[project]\nname = "ddev"\nversion = "1.0"\n\n[project.optional-dependencies]\ndeps = ["ddev-dep==1.0"]\n',
    )
    _write_pyproject(repo, 'tooling', '[tool.some]\nkey = "value"\n')
    return repo


def test_enumeration_excludes_non_checks_and_unnamed_pyprojects(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    checks = generate_per_check_requirements.per_check_requirements(repo)

    assert sorted(checks) == ['datadog_checks_base', 'postgres', 'redisdb']


def test_requirement_sets_are_base_closure_plus_deps_extra(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    base_closure = BASE_DEPS_GROUP + BASE_HTTP_GROUP

    checks = generate_per_check_requirements.per_check_requirements(repo)

    assert checks['datadog_checks_base'] == base_closure
    assert checks['redisdb'] == base_closure
    assert checks['postgres'] == base_closure + ['psycopg==3.3.4']
