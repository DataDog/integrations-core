# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Direct tests for `format_with_ruff` and `_resolve_ruff_config`.

The helper is exercised end-to-end by `ddev validate models -s`, but only
when generated content crosses 120 characters or normalization is needed.
These tests pin the behavior the validate flow relies on so a future
refactor or library bump can't silently break it.
"""

from pathlib import Path

import pytest

from datadog_checks.dev.tooling.configuration.consumers.model import code_formatter
from datadog_checks.dev.tooling.configuration.consumers.model.code_formatter import (
    _has_ruff_section,
    _resolve_ruff_config,
    format_with_ruff,
)

# --- format_with_ruff -------------------------------------------------------

LONG_DICT_LITERAL = (
    "x = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8, 'i': 9, "
    "'j': 10, 'k': 11, 'l': 12, 'm': 13, 'n': 14, 'o': 15, 'p': 16, 'q': 17, "
    "'r': 18, 's': 19, 't': 20}\n"
)


def test_format_with_ruff_wraps_lines_longer_than_120():
    formatted = format_with_ruff(LONG_DICT_LITERAL)
    # The original is a single line well over 120 chars; ruff must split it
    # into multiple lines, and every output line must be <= 120 chars.
    assert formatted.count('\n') > 1
    for line in formatted.splitlines():
        assert len(line) <= 120, f'unexpected long line: {line!r}'


def test_format_with_ruff_preserves_quote_style():
    # Repo-wide ruff config sets format.quote-style=preserve (matching the
    # legacy black skip-string-normalization). Single quotes must survive.
    formatted = format_with_ruff(LONG_DICT_LITERAL)
    assert "'a'" in formatted and '"a"' not in formatted


def test_format_with_ruff_short_input_passes_through_unchanged():
    source = "x = 1\n"
    assert format_with_ruff(source) == source


def test_format_with_ruff_surfaces_install_hint_when_ruff_module_missing(monkeypatch):
    """If `python -m ruff` exits with `No module named 'ruff'` the helper must
    surface the actionable reinstall hint instead of the raw stderr."""
    import subprocess

    def fake_run(args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=args,
            output='',
            stderr="/usr/bin/python: No module named 'ruff'\n",
        )

    monkeypatch.setattr(code_formatter.subprocess, 'run', fake_run)
    with pytest.raises(RuntimeError, match='`ruff` package is not installed'):
        format_with_ruff('x = 1\n')


def test_format_with_ruff_includes_argv_and_streams_on_other_failures(monkeypatch):
    """For non-missing-package failures the error message must include
    enough context (argv, stderr, stdout) to reproduce the failure."""
    import subprocess

    def fake_run(args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=2,
            cmd=args,
            output='partial output',
            stderr='unexpected ruff error',
        )

    monkeypatch.setattr(code_formatter.subprocess, 'run', fake_run)
    with pytest.raises(RuntimeError) as excinfo:
        format_with_ruff('x = 1\n')

    msg = str(excinfo.value)
    assert 'unexpected ruff error' in msg
    assert 'partial output' in msg
    assert 'ruff' in msg and 'format' in msg  # argv components surface


# --- _resolve_ruff_config ---------------------------------------------------


def _write_pyproject(directory: Path, body: str) -> Path:
    pyproject = directory / 'pyproject.toml'
    pyproject.write_text(body)
    return pyproject


def test_resolve_uses_root_when_get_root_points_to_a_pyproject_with_ruff(monkeypatch, tmp_path):
    pyproject = _write_pyproject(
        tmp_path,
        '[tool.ruff]\nline-length = 120\n',
    )
    monkeypatch.setattr(code_formatter, 'get_root', lambda: str(tmp_path))

    assert _resolve_ruff_config() == pyproject


def test_resolve_falls_back_to_module_walk_when_get_root_is_empty(monkeypatch):
    """Unit tests don't call `set_root`, so `get_root()` returns ''. The
    helper must walk up from the module path and find the repo pyproject.toml,
    not probe the test runner's CWD."""
    monkeypatch.setattr(code_formatter, 'get_root', lambda: '')

    resolved = _resolve_ruff_config()

    assert resolved is not None
    assert resolved.name == 'pyproject.toml'
    # The module lives at <repo>/datadog_checks_dev/datadog_checks/dev/tooling/
    # configuration/consumers/model/code_formatter.py, so the resolved config
    # must be one of its ancestor pyproject.toml files.
    module_file = Path(code_formatter.__file__).resolve()
    assert resolved in {parent / 'pyproject.toml' for parent in module_file.parents}
    # Sanity-check the file actually has the central ruff settings.
    assert _has_ruff_section(resolved)


def test_resolve_falls_back_when_root_pyproject_has_no_ruff_section(monkeypatch, tmp_path):
    """If `get_root()` points at a directory whose pyproject.toml has no
    `[tool.ruff]`, the helper must fall through to the module-path walk
    rather than returning a config that ruff would ignore."""
    _write_pyproject(tmp_path, '[project]\nname = "x"\n')
    monkeypatch.setattr(code_formatter, 'get_root', lambda: str(tmp_path))

    resolved = _resolve_ruff_config()

    assert resolved is not None
    assert resolved != tmp_path / 'pyproject.toml'


def test_resolve_returns_none_when_nothing_can_be_found(monkeypatch, tmp_path):
    monkeypatch.setattr(code_formatter, 'get_root', lambda: '')
    # Repoint __file__ to a tree that has no pyproject.toml above it.
    inner = tmp_path / 'a' / 'b' / 'c'
    inner.mkdir(parents=True)
    monkeypatch.setattr(code_formatter, '__file__', str(inner / 'code_formatter.py'))

    assert _resolve_ruff_config() is None


# --- _has_ruff_section ------------------------------------------------------


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        ('[tool.ruff]\nline-length = 120\n', True),
        ('[tool.ruff.lint]\nselect = ["E"]\n', True),
        ('[tool.ruff.format]\nquote-style = "preserve"\n', True),
        ('[project]\nname = "x"\n', False),
        ('# Migrate from [tool.ruff.lint.format] later\n', False),  # comment, not header
        ('description = "explains [tool.ruff] elsewhere"\n', False),  # value, not header
        ('', False),
    ],
)
def test_has_ruff_section_only_matches_actual_table_headers(tmp_path, body, expected):
    pyproject = _write_pyproject(tmp_path, body)
    assert _has_ruff_section(pyproject) is expected


def test_has_ruff_section_returns_false_for_missing_file(tmp_path):
    assert _has_ruff_section(tmp_path / 'does-not-exist.toml') is False
