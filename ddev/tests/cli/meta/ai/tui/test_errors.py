# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for tui/errors.py: compacting error text for single-line surfaces."""

from __future__ import annotations

from ddev.cli.meta.ai.tui.errors import BANNER_ERROR_MAX_CHARS, compact_error_detail


def test_single_line_error_is_returned_unchanged() -> None:
    assert compact_error_detail("Checkpoints must be a mapping.") == "Checkpoints must be a mapping."


def test_only_the_first_non_empty_line_survives() -> None:
    """A YAML parse error carries the offending source and a caret on later lines."""
    error = 'Failed to load checkpoints: while parsing a flow mapping\n  in "<unicode string>", line 1\n    ^'
    assert compact_error_detail(error) == "Failed to load checkpoints: while parsing a flow mapping"


def test_leading_blank_lines_are_skipped() -> None:
    assert compact_error_detail("\n\n  the real message  \n more") == "the real message"


def test_long_line_is_truncated_with_an_ellipsis() -> None:
    detail = compact_error_detail("x" * (BANNER_ERROR_MAX_CHARS + 50))
    assert len(detail) == BANNER_ERROR_MAX_CHARS
    assert detail.endswith("…")


def test_max_chars_is_configurable() -> None:
    assert compact_error_detail("abcdefghij", max_chars=5) == "abcd…"


def test_blank_error_collapses_to_empty() -> None:
    assert compact_error_detail("   \n  \n") == ""


def test_pydantic_validation_text_loses_its_bracketed_fragments() -> None:
    """The bracketed fragments that break Textual markup live on lines after the first."""
    error = (
        "Checkpoint for phase 'phase_0' is invalid: 4 validation errors\n"
        "success.started_at\n"
        "  Field required [type=missing, input_value={'status': 'success'}, input_type=dict]\n"
    )
    detail = compact_error_detail(error)
    assert detail == "Checkpoint for phase 'phase_0' is invalid: 4 validation errors"
    assert "input_value=" not in detail
