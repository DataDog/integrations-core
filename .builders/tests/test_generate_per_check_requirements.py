"""Tests for generate_per_check_requirements.py: enumeration and closure resolution."""

from __future__ import annotations

import importlib
import json
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


def _report_entry(name: str, version: str, wheel_path: str) -> dict:
    return {
        'metadata': {'name': name, 'version': version},
        'download_info': {'url': f'file://{wheel_path}'},
    }


def test_parse_closure_report_extracts_sorted_wheels() -> None:
    report = {
        'install': [
            _report_entry('psycopg', '3.3.4', '/wheels/external/psycopg-3.3.4-py3-none-any.whl'),
            _report_entry('binary', '1.0.2', '/wheels/built/binary-1.0.2-py3-none-any.whl'),
        ]
    }

    closure = generate_per_check_requirements.parse_closure_report(report)

    assert closure == [
        generate_per_check_requirements.ResolvedWheel('binary', '1.0.2', 'binary-1.0.2-py3-none-any.whl'),
        generate_per_check_requirements.ResolvedWheel('psycopg', '3.3.4', 'psycopg-3.3.4-py3-none-any.whl'),
    ]


def test_resolve_closure_builds_command_and_parses_report(tmp_path: Path) -> None:
    requirements = ['binary==1.0.2', 'psycopg[c,pool]==3.3.4']
    wheel_dirs = [tmp_path / 'built', tmp_path / 'external']
    wheel_dirs[0].mkdir()
    wheel_dirs[1].mkdir()
    commands: list[list[str]] = []
    requirements_contents: list[str] = []

    def fake_runner(command: list[str]) -> object:
        commands.append(command)
        requirements_contents.append(Path(command[command.index('-r') + 1]).read_text(encoding='utf-8'))
        report_path = Path(command[command.index('--report') + 1])
        report_path.write_text(
            json.dumps(
                {
                    'install': [
                        _report_entry('binary', '1.0.2', f'{wheel_dirs[0]}/binary-1.0.2-py3-none-any.whl'),
                        _report_entry('psycopg', '3.3.4', f'{wheel_dirs[1]}/psycopg-3.3.4-py3-none-any.whl'),
                    ]
                }
            ),
            encoding='utf-8',
        )
        return None

    closure = generate_per_check_requirements.resolve_closure(
        requirements, wheel_dirs, Path('/py3/bin/python'), fake_runner
    )

    assert len(commands) == 1
    command = commands[0]
    assert command[:9] == [
        '/py3/bin/python',
        '-m',
        'pip',
        'install',
        '--dry-run',
        '--ignore-installed',
        '--no-index',
        '--only-binary',
        ':all:',
    ]
    find_links = [command[i + 1] for i, arg in enumerate(command) if arg == '--find-links']
    assert find_links == [str(wheel_dirs[0]), str(wheel_dirs[1])]
    assert requirements_contents == ['\n'.join(requirements) + '\n']
    assert closure == [
        generate_per_check_requirements.ResolvedWheel('binary', '1.0.2', 'binary-1.0.2-py3-none-any.whl'),
        generate_per_check_requirements.ResolvedWheel('psycopg', '3.3.4', 'psycopg-3.3.4-py3-none-any.whl'),
    ]
