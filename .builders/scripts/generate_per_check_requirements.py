"""Per-check requirement sets for per-integration dependency lockfiles.

Each check's set is the union of every optional-dependencies group of
`datadog_checks_base` (the shared base environment every check installs
into) and the check's own `deps` extra. Requirement lines are taken
verbatim from pyproject.toml files so environment markers are evaluated
against the builder's target platform.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

BASE_CHECK = 'datadog_checks_base'
DEPS_EXTRA = 'deps'
EXCLUDED_PACKAGES = frozenset({'datadog_checks_dev', 'datadog_checks_tests_helper', 'ddev'})


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
