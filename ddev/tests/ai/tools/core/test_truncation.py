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


class TestExtractErrorLines:
    @pytest.mark.parametrize("keyword", ["ERROR", "FAILED", "Exception", "Traceback", "fatal", "panic"])
    def test_detects_each_error_keyword(self, keyword: str):
        lines = ["normal line", f"this is a {keyword} here", "another normal"]
        result = extract_error_lines(lines)
        assert len(result) == 1
        assert result[0][1] == f"this is a {keyword} here"

    @pytest.mark.parametrize("keyword", ["error", "failed", "exception", "traceback", "FATAL", "PANIC"])
    def test_matching_is_case_insensitive(self, keyword: str):
        lines = [f"line with {keyword}"]
        result = extract_error_lines(lines)
        assert len(result) == 1

    def test_returns_correct_index(self):
        lines = ["ok", "ok", "ERROR: boom", "ok"]
        result = extract_error_lines(lines)
        assert result[0][0] == 2

    def test_returns_multiple_matching_lines(self):
        lines = ["ERROR: first", "normal", "Traceback: second"]
        result = extract_error_lines(lines)
        assert len(result) == 2

    def test_clean_content_returns_empty(self):
        lines = ["everything", "is", "fine"]
        assert extract_error_lines(lines) == []

    def test_empty_input_returns_empty(self):
        assert extract_error_lines([]) == []


# ---------------------------------------------------------------------------
# truncate — no truncation needed
# ---------------------------------------------------------------------------


class TestTruncateNoOp:
    def test_short_content_returned_unchanged(self):
        content = "hello world"
        result = truncate(content, max_chars=MAX_CHARS)
        assert result.output == content
        assert result.truncated is False
        assert result.meta is None

    def test_content_exactly_at_limit_not_truncated(self):
        content = make_content(MAX_CHARS)
        result = truncate(content, max_chars=MAX_CHARS)
        assert result.truncated is False

    def test_content_one_over_limit_is_truncated(self):
        content = make_content(MAX_CHARS + 1)
        result = truncate(content, max_chars=MAX_CHARS)
        assert result.truncated is True


# ---------------------------------------------------------------------------
# truncate — basic head+tail (no errors)
# ---------------------------------------------------------------------------


class TestTruncateBasic:
    def setup_method(self):
        # Use a small max_chars to keep tests fast and readable
        self.max_chars = 100
        self.content = make_content(500)

    def test_output_length_within_budget(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert len(result.output) <= self.max_chars + 150  # gap marker adds ~50 chars

    def test_truncated_flag_is_true(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert result.truncated is True

    def test_meta_is_set(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert result.meta is not None

    def test_meta_total_size_equals_input_length(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert result.meta.total_size == len(self.content)

    def test_meta_shown_size_matches_output_length(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert result.meta.shown_size == len(result.output)

    def test_meta_truncated_size_is_difference(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert result.meta.truncated_size == result.meta.total_size - result.meta.shown_size

    def test_gap_marker_present_in_output(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert "[..." in result.output and "characters removed" in result.output

    def test_head_comes_from_start_of_content(self):
        content = "START" + "x" * 500 + "END"
        result = truncate(content, max_chars=self.max_chars)
        assert result.output.startswith("START")

    def test_tail_comes_from_end_of_content(self):
        content = "START" + "x" * 500 + "END"
        result = truncate(content, max_chars=self.max_chars)
        assert result.output.endswith("END")

    def test_hint_mentions_shown_and_total(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert str(result.meta.shown_size) in result.meta.hint
        assert str(result.meta.total_size) in result.meta.hint


# ---------------------------------------------------------------------------
# truncate — error-aware preservation
# ---------------------------------------------------------------------------


class TestTruncateErrorAware:
    def setup_method(self):
        self.max_chars = 200
        padding = "x" * 80 + "\n"
        middle_error = "ERROR: critical failure detected\n"
        self.content = padding * 5 + middle_error + padding * 5

    def test_error_line_preserved_in_output(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert "ERROR: critical failure detected" in result.output

    def test_gap_marker_mentions_errors_preserved(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert "errors preserved" in result.output

    def test_meta_hint_does_not_mention_dropped_errors(self):
        result = truncate(self.content, max_chars=self.max_chars)
        assert "could not be preserved" not in result.meta.hint

    @pytest.mark.parametrize("keyword", ["FAILED", "Exception", "Traceback", "fatal", "panic"])
    def test_each_error_keyword_triggers_preservation(self, keyword: str):
        padding = "y" * 80 + "\n"
        content = padding * 5 + f"{keyword}: something bad\n" + padding * 5
        result = truncate(content, max_chars=self.max_chars)
        assert keyword in result.output


# ---------------------------------------------------------------------------
# truncate — errors too large to preserve (fallback to plain head+tail)
# ---------------------------------------------------------------------------


class TestTruncateErrorsDropped:
    def test_falls_back_to_plain_truncation_when_error_snippet_exceeds_budget(self):
        max_chars = 200
        error_lines = "\n".join([f"ERROR: line {i}" for i in range(50)])  # ~700 chars of errors
        padding = "x" * 80 + "\n"
        content = padding * 5 + error_lines + padding * 5

        result = truncate(content, max_chars=max_chars)

        assert result.truncated is True
        assert "could not be preserved" in result.meta.hint
        assert "errors preserved" not in result.output
