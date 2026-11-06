# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pin the ddtrace APIs that datadog_checks_base imports.

Two of the import sites in ``checks/base.py`` are unguarded and run at module scope, behind
the ``integration_tracing`` and ``integration_profiling`` config flags. A ddtrace release
that drops one of those APIs makes ``datadog_checks.base`` unimportable, and so breaks every
integration -- but only for users who turned those flags on, which the rest of the suite
never does. Nothing else imports them, so nothing else notices.

Sites are discovered from the source rather than listed here, so a new ddtrace import
anywhere in the package is covered without editing this file. Imports that a ``try`` already
protects are left out on purpose: those degrade to untraced checks instead of breaking.
"""

import ast
from pathlib import Path

import pytest

import datadog_checks.base

ddtrace = pytest.importorskip('ddtrace')

PACKAGE_ROOT = Path(datadog_checks.base.__file__).parent
# Handlers that turn an import failure into something the check survives.
SWALLOWED_EXCEPTIONS = frozenset({'ImportError', 'ModuleNotFoundError', 'Exception', 'BaseException'})


def _imports_ddtrace(node):
    if isinstance(node, ast.ImportFrom):
        # Relative imports (`from . import x`) carry module=None and can never be ddtrace.
        names = [node.module or '']
    else:
        names = [alias.name for alias in node.names]

    return any(name == 'ddtrace' or name.startswith('ddtrace.') for name in names)


def _swallows_import_errors(node):
    for handler in node.handlers:
        if handler.type is None:  # bare `except:`
            return True

        caught = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
        if any(isinstance(exc, ast.Name) and exc.id in SWALLOWED_EXCEPTIONS for exc in caught):
            return True

    return False


def _collect(node, relative_path, guarded, found):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        if not guarded and _imports_ddtrace(node):
            found.append((ast.unparse(node), f'{relative_path}:{node.lineno}'))
        return

    if isinstance(node, ast.Try) and _swallows_import_errors(node):
        for child in [*node.body, *node.handlers, *node.orelse]:
            _collect(child, relative_path, True, found)
        # A `finally` block runs whether or not the handlers fire, so it stays unprotected.
        for child in node.finalbody:
            _collect(child, relative_path, guarded, found)
        return

    for child in ast.iter_child_nodes(node):
        _collect(child, relative_path, guarded, found)


def _unguarded_ddtrace_imports():
    found = []
    for path in sorted(PACKAGE_ROOT.rglob('*.py')):
        # filename= keeps any SyntaxWarning the package source emits attributable;
        # ast.parse otherwise blames `<unknown>`.
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        _collect(tree, path.relative_to(PACKAGE_ROOT), False, found)

    return found


UNGUARDED_IMPORTS = _unguarded_ddtrace_imports()


def test_discovery_finds_import_sites():
    # Without this, the parametrized test below passes vacuously if discovery ever breaks.
    assert UNGUARDED_IMPORTS, f'no unguarded ddtrace imports discovered under {PACKAGE_ROOT}'


@pytest.mark.parametrize(
    ('statement', 'location'),
    UNGUARDED_IMPORTS,
    ids=[location for _, location in UNGUARDED_IMPORTS],
)
def test_unguarded_ddtrace_import_resolves(statement, location):
    try:
        exec(compile(statement, location, 'exec'), {})
    except ImportError as e:
        pytest.fail(
            f'{location}: `{statement}` does not resolve against ddtrace {ddtrace.__version__} ({e}). '
            'It runs at module scope, so datadog_checks.base becomes unimportable for anyone who has '
            'integration_tracing or integration_profiling enabled.'
        )
