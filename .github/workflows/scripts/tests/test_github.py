"""Tests for _release.github."""
import pytest

from _release.github import parse_bool_env, set_outputs, write_summary


class TestParseBoolEnv:
    def test_true_values(self, monkeypatch):
        for val in ("true", "True", "TRUE", "1", "yes", "YES"):
            monkeypatch.setenv("MY_FLAG", val)
            assert parse_bool_env("MY_FLAG") is True, f"Expected True for {val!r}"

    def test_false_values(self, monkeypatch):
        for val in ("false", "False", "FALSE", "0", "no", "NO"):
            monkeypatch.setenv("MY_FLAG", val)
            assert parse_bool_env("MY_FLAG") is False, f"Expected False for {val!r}"

    def test_missing_uses_default_false(self, monkeypatch):
        monkeypatch.delenv("MY_FLAG", raising=False)
        assert parse_bool_env("MY_FLAG", default=False) is False

    def test_missing_uses_default_true(self, monkeypatch):
        monkeypatch.delenv("MY_FLAG", raising=False)
        assert parse_bool_env("MY_FLAG", default=True) is True

    def test_empty_string_uses_default(self, monkeypatch):
        monkeypatch.setenv("MY_FLAG", "")
        assert parse_bool_env("MY_FLAG", default=False) is False
        assert parse_bool_env("MY_FLAG", default=True) is True

    def test_whitespace_only_uses_default(self, monkeypatch):
        monkeypatch.setenv("MY_FLAG", "  ")
        assert parse_bool_env("MY_FLAG", default=False) is False


class TestSetOutputs:
    def test_writes_key_value_pairs(self, tmp_path, monkeypatch):
        out = tmp_path / "output"
        out.write_text("")
        monkeypatch.setenv("GITHUB_OUTPUT", str(out))
        set_outputs(foo="bar", baz="qux")
        content = out.read_text()
        assert "foo=bar\n" in content
        assert "baz=qux\n" in content

    def test_no_file_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        set_outputs(key="value")  # should not raise


class TestWriteSummary:
    def test_appends_content(self, tmp_path, monkeypatch):
        summary = tmp_path / "summary.md"
        summary.write_text("# Existing\n")
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
        write_summary("## New Section")
        assert "## New Section" in summary.read_text()
        assert "# Existing" in summary.read_text()

    def test_no_op_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        write_summary("content")  # should not raise
