# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.ai.tools.core.truncation import MAX_CHARS, extract_error_lines, truncate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_content(n_chars: int, char: str = "x") -> str:
    """Build a string of exactly n_chars characters."""
    return char * n_chars


def make_content_with_error(total: int, error_line: str = "ERROR: something failed") -> str:
    """Build a string longer than MAX_CHARS with an error line in the middle."""
    half = total // 2
    padding = "x" * 80 + "\n"
    before = padding * (half // len(padding) + 1)
    after = padding * (half // len(padding) + 1)
    return before[:half] + "\n" + error_line + "\n" + after[:half]


# ---------------------------------------------------------------------------
# extract_error_lines
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "keyword",
    [
        "ERROR",
        "FAILED",
        "Exception",
        "Traceback",
        "fatal",
        "panic",
        "error",
        "failed",
        "exception",
        "traceback",
        "FATAL",
        "PANIC",
    ],
)
def test_detects_each_error_keyword_case_insensitive(keyword: str):
    lines = ["normal line", f"this is a {keyword} here", "another normal"]
    result = extract_error_lines(lines)
    assert len(result) == 1


def test_extract_error_lines_returns_correct_index():
    lines = ["ok", "ok", "ERROR: boom", "ok"]
    result = extract_error_lines(lines)
    assert result[0][0] == 2


def test_extract_error_lines_returns_multiple_matching_lines():
    lines = ["ERROR: first", "normal", "Traceback: second"]
    result = extract_error_lines(lines)
    assert len(result) == 2


def test_extract_error_lines_clean_content_returns_empty():
    lines = ["everything", "is", "fine"]
    assert extract_error_lines(lines) == []


def test_extract_error_lines_empty_input_returns_empty():
    assert extract_error_lines([]) == []


# ---------------------------------------------------------------------------
# truncate — max_char limit works as expected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content,expected_truncated",
    [
        ("hello world", False),
        (make_content(MAX_CHARS), False),
        (make_content(MAX_CHARS + 1), True),
    ],
)
def test_max_char_limit(content, expected_truncated):
    result = truncate(content, max_chars=MAX_CHARS)
    assert result.truncated is expected_truncated
    if not expected_truncated:
        assert result.meta is None


# ---------------------------------------------------------------------------
# truncate — basic head+tail (no errors)
# ---------------------------------------------------------------------------


@pytest.fixture
def content() -> str:
    return make_content(500)


@pytest.fixture
def max_chars() -> int:
    return 200


def test_truncate_basic_head_tail_no_errors(content: str, max_chars: int):
    result = truncate(content, max_chars=max_chars)
    assert len(result.output) <= max_chars + 150  # gap marker adds ~50 chars
    assert result.truncated is True

    assert result.meta is not None
    assert result.meta.total_size == len(content)
    assert result.meta.shown_size == len(result.output)
    assert result.meta.truncated_size == result.meta.total_size - result.meta.shown_size

    assert "[..." in result.output and "characters removed" in result.output

    assert str(result.meta.shown_size) in result.meta.hint
    assert str(result.meta.total_size) in result.meta.hint


def test_truncate_starts_and_ends_with_content(content: str, max_chars: int):
    content = "START" + content + "END"
    result = truncate(content, max_chars=max_chars)
    assert result.output.startswith("START")
    assert result.output.endswith("END")


# ---------------------------------------------------------------------------
# truncate — error-aware preservation
# ---------------------------------------------------------------------------


@pytest.fixture
def content_with_error() -> str:
    padding = "x" * 80 + "\n"
    middle_error = "ERROR: critical failure detected\n"
    return padding * 5 + middle_error + padding * 5


def test_error_aware_preservation(content_with_error: str, max_chars: int):
    result = truncate(content_with_error, max_chars=max_chars)
    assert "ERROR: critical failure detected" in result.output
    assert "errors preserved" in result.output
    assert "could not be preserved" not in result.meta.hint


@pytest.mark.parametrize("keyword", ["FAILED", "Exception", "Traceback", "fatal", "panic"])
def test_each_error_keyword_triggers_preservation(keyword: str):
    padding = "y" * 80 + "\n"
    content = padding * 5 + f"{keyword}: something bad\n" + padding * 5
    result = truncate(content, max_chars=200)
    assert keyword in result.output


# ---------------------------------------------------------------------------
# truncate — errors too large to preserve (fallback to plain head+tail)
# ---------------------------------------------------------------------------


def test_falls_back_to_plain_truncation_when_error_snippet_exceeds_budget():
    max_chars = 200
    error_lines = "\n".join([f"ERROR: line {i}" for i in range(50)])  # ~700 chars of errors
    padding = "x" * 80 + "\n"
    content = padding * 5 + error_lines + padding * 5

    result = truncate(content, max_chars=max_chars)

    assert result.truncated is True
    assert "could not be preserved" in result.meta.hint
    assert "errors preserved" not in result.output
