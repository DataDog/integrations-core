"""Per-check requirement sets and wheel-closure resolution for per-integration lockfiles.

Each check's set is the union of every optional-dependencies group of
`datadog_checks_base` (the shared base environment every check installs
into) and the check's own `deps` extra. Requirement lines are taken
verbatim from pyproject.toml files so environment markers are evaluated
against the builder's target platform.

Closures are resolved with the builder's own pip against the wheelhouse the
union build already staged (`--no-index --find-links`), so resolution uses
exactly the wheels that will be published, including internal-built wheels
that have no PyPI presence.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import NamedTuple

BASE_CHECK = 'datadog_checks_base'
DEPS_EXTRA = 'deps'
EXCLUDED_PACKAGES = frozenset({'datadog_checks_dev', 'datadog_checks_tests_helper', 'ddev'})


class ResolvedWheel(NamedTuple):
    name: str
    version: str
    wheel_file: str


def base_requirements(repo_root: Path) -> list[str]:
    """Return the flattened optional-dependencies of `datadog_checks_base`."""
    with (repo_root / BASE_CHECK / 'pyproject.toml').open('rb') as f:
        data = tomllib.load(f)
    groups = data['project']['optional-dependencies']
    return [line for group_lines in groups.values() for line in group_lines]


def per_check_requirements(repo_root: Path) -> dict[str, list[str]]:
    """Return check directory name -> requirement lines.

    Every requirement set starts from the shared base closure; exact duplicate
    lines are dropped so the set stays minimal without changing resolution.
    pyproject.toml files without a `[project]` name (e.g. tooling config) are
    skipped.
    """
    base = base_requirements(repo_root)
    checks: dict[str, list[str]] = {}
    for pyproject in sorted(repo_root.glob('*/pyproject.toml')):
        check = pyproject.parent.name
        if check in EXCLUDED_PACKAGES:
            continue
        with pyproject.open('rb') as f:
            data = tomllib.load(f)
        project = data.get('project', {})
        if 'name' not in project:
            continue
        requirements = base + project.get('optional-dependencies', {}).get(DEPS_EXTRA, [])
        checks[check] = list(dict.fromkeys(requirements))
    return checks


def resolve_command(
    python_path: Path,
    wheel_dirs: list[Path],
    requirements_file: Path,
    report_file: Path,
) -> list[str]:
    """Return the pip dry-run command that resolves `requirements_file` against `wheel_dirs`.

    `--ignore-installed` is required for report completeness: without it pip
    omits requirements already satisfied in the builder environment from the
    report, which would silently punch holes in the closure.
    """
    command = [
        str(python_path),
        '-m',
        'pip',
        'install',
        '--dry-run',
        '--ignore-installed',
        '--no-index',
        '--only-binary',
        ':all:',
    ]
    for wheel_dir in wheel_dirs:
        command += ['--find-links', str(wheel_dir)]
    return command + ['--report', str(report_file), '-r', str(requirements_file)]


def parse_closure_report(report: dict) -> list[ResolvedWheel]:
    """Extract the resolved distributions from a pip install report."""
    return sorted(
        ResolvedWheel(
            item['metadata']['name'],
            item['metadata']['version'],
            item['download_info']['url'].rsplit('/', 1)[-1],
        )
        for item in report['install']
    )


def resolve_closure(
    requirements: list[str],
    wheel_dirs: list[Path],
    python_path: Path,
    runner: Callable[[list[str]], object],
) -> list[ResolvedWheel]:
    """Resolve `requirements` to their exact wheel closure from `wheel_dirs`.

    `runner` executes the resolver command and must fail the build on a
    nonzero exit (e.g. build_wheels.check_process); resolution errors must
    not produce a partial closure.
    """
    with TemporaryDirectory() as td:
        requirements_file = Path(td) / 'requirements.txt'
        requirements_file.write_text('\n'.join(requirements) + '\n', encoding='utf-8')
        report_file = Path(td) / 'report.json'
        runner(resolve_command(python_path, wheel_dirs, requirements_file, report_file))
        return parse_closure_report(json.loads(report_file.read_text(encoding='utf-8')))
