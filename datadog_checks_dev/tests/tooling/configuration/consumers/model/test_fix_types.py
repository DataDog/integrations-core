# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Focused tests for the `_fix_types` post-processing pass.

`_fix_types` is responsible for translating mutable container annotations
emitted by the parser (`list[X]`, `dict[K, V]`) into their immutable
equivalents (`tuple[X, ...]`, `MappingProxyType[K, V]`). The bracket-tracking
walker that adds the `, ...` ellipsis must work whether the annotation lives
on a single line or has been wrapped across many lines by the upstream
formatter; the latter case is what made dropping the `[tool.black]` config
block from `pyproject.toml` viable.
"""

import pytest

from datadog_checks.dev.tooling.configuration.consumers.model.model_file import _fix_types


def _run(source: str) -> str:
    lines = source.split('\n')
    _fix_types(lines)
    return '\n'.join(lines)


def test_dict_is_replaced_with_mapping_proxy_type():
    assert _run('headers: dict[str, str]') == 'headers: MappingProxyType[str, str]'


def test_list_on_single_line_becomes_variable_length_tuple():
    assert _run('tags: list[str]') == 'tags: tuple[str, ...]'


def test_nested_lists_each_get_their_own_ellipsis():
    assert _run('matrix: list[list[int]]') == 'matrix: tuple[tuple[int, ...], ...]'


def test_non_list_non_dict_input_is_returned_unchanged_verbatim():
    # Lines that contain neither `list[` nor `dict[` are left alone byte-for-byte.
    source = "vals: Optional[Mapping[str, int]] = compute(arg)"
    assert _run(source) == source


def test_list_of_literal_wrapped_across_multiple_lines():
    """Regression: when the upstream parser pre-wraps `list[Literal[...]]`
    across lines (because black's default 88-char line-length is exceeded by
    the inner Literal), the per-line walker that used to live here would
    silently drop the `, ...` sentinel and emit `tuple[Literal[...]]`
    (single-element tuple) — a real type-contract change. Whole-document
    bracket tracking preserves the variable-length tuple."""
    source = (
        "    states: Optional[\n"
        "        list[\n"
        "            Literal[\n"
        "                'ALL',\n"
        "                'NEW',\n"
        "                'NEW_SAVING',\n"
        "                'SUBMITTED',\n"
        "                'ACCEPTED',\n"
        "                'RUNNING',\n"
        "                'FINISHED',\n"
        "                'FAILED',\n"
        "                'KILLED',\n"
        "            ]\n"
        "        ]\n"
        "    ] = None"
    )
    out = _run(source)
    # The `list` opener becomes `tuple` and gets a `, ...` sentinel before its
    # matching `]`; the inner Literal brackets are untouched.
    assert 'list[' not in out
    assert 'tuple[' in out
    # The sentinel lands on the same line as the inner `]` of the Literal
    # (immediately after the last non-whitespace byte), not on a line of its own.
    assert '            ], ...\n        ]\n    ] = None' in out


def test_unicode_inside_descriptions_does_not_break_walker():
    """The walker iterates UTF-8 bytes so multi-byte sequences in field
    descriptions, examples, etc. don't trip the `byte must be in range(0, 256)`
    error the original char-iterating implementation would raise."""
    source = "label: Optional[list[str]] = Field(\n    None, description='unicode: ✓ — résumé · 日本語'\n)"
    out = _run(source)
    assert 'tuple[str, ...]' in out
    assert '✓' in out
    assert '日本語' in out


@pytest.mark.parametrize(
    ('input_line', 'expected_line'),
    [
        # Nested list inside Optional, single line.
        ('Optional[list[int]]', 'Optional[tuple[int, ...]]'),
        # list and dict combined on the same line.
        ('list[dict[str, int]]', 'tuple[MappingProxyType[str, int], ...]'),
    ],
)
def test_simple_combinations(input_line: str, expected_line: str):
    assert _run(input_line) == expected_line


def test_no_list_no_dict_input_is_returned_unchanged():
    source = "name: str = Field('default', examples=['x'])"
    assert _run(source) == source
