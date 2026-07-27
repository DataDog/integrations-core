# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.cli.application import Application

LEGACY_HTTP_OPTIONS_ALIASES = frozenset(
    {
        'http',
        '_http',
        'requests_wrapper',
        'http_handler',
        'handler',
        'client',
        'mock_http',
        'fake',
    }
)

LEGACY_HTTP_OPTIONS_EXCLUDED_FILES = frozenset(
    {
        'datadog_checks_base/datadog_checks/base/utils/http.py',
    }
)

_SKIP_DIR_NAMES = frozenset({'.git', '.venv', '__pycache__', 'node_modules', '.hatch'})


def _is_legacy_http_options_access(node: ast.AST) -> bool:
    if not isinstance(node, ast.Attribute) or node.attr != 'options':
        return False

    value = node.value
    if isinstance(value, ast.Name):
        return value.id in LEGACY_HTTP_OPTIONS_ALIASES
    if isinstance(value, ast.Attribute):
        return value.attr in LEGACY_HTTP_OPTIONS_ALIASES
    return False


def count_legacy_http_options_accesses(path: Path) -> int:
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return 0

    return sum(1 for node in ast.walk(tree) if _is_legacy_http_options_access(node))


def collect_legacy_http_options_accesses(repo_root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in repo_root.rglob('*.py'):
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue

        relative_path = path.relative_to(repo_root).as_posix()
        if relative_path in LEGACY_HTTP_OPTIONS_EXCLUDED_FILES:
            continue

        count = count_legacy_http_options_accesses(path)
        if count:
            counts[relative_path] = count

    return counts


def validate_legacy_http_options_accesses(app: Application) -> list[str]:
    """Fail on any legacy HTTP-client .options access outside RequestsWrapper internals."""
    repo_root = app.repo.path
    actual = collect_legacy_http_options_accesses(repo_root)

    errors: list[str] = []
    for path, count in sorted(actual.items()):
        errors.append(
            f'Legacy HTTP options access in {path} ({count} occurrence(s)). '
            f'Use HTTPClient capabilities instead of .options.'
        )

    return errors
