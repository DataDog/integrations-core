# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
from dataclasses import dataclass
from typing import Annotated
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ddev.ai.tools.core.truncation import MAX_CHARS
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.shell.base import CmdTool, run_command

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    """Build a mock subprocess object."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    return proc


def patch_proc(proc: MagicMock):
    """Patch asyncio.create_subprocess_exec to return proc."""
    return patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc))


# ---------------------------------------------------------------------------
# Minimal CmdTool subclass for testing
# ---------------------------------------------------------------------------


@dataclass
class GreetInput:
    name: Annotated[str, "Name to greet"]


class GreetTool(CmdTool[GreetInput]):
    """Greet someone."""

    @property
    def name(self) -> str:
        return "greet"

    def cmd(self, tool_input: GreetInput) -> list[str]:
        return ["echo", f"hello {tool_input.name}"]


class SlowGreetTool(GreetTool):
    timeout = 60


# ---------------------------------------------------------------------------
# run_command — successful execution
# ---------------------------------------------------------------------------


class TestRunCommandSuccess:
    def test_returns_success_true_on_zero_exit(self):
        proc = make_proc(returncode=0, stdout=b"hello\n")
        with patch_proc(proc):
            result = asyncio.run(run_command(["echo", "hello"]))
        assert result.success is True

    def test_returns_stdout_as_data(self):
        proc = make_proc(returncode=0, stdout=b"some output\n")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.data == "some output\n"

    def test_ignores_stderr_on_zero_exit(self):
        proc = make_proc(returncode=0, stdout=b"out\n", stderr=b"warning\n")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.data == "out\n"
        assert "warning" not in result.data

    def test_not_truncated_for_short_output(self):
        proc = make_proc(stdout=b"short\n")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.truncated is False


# ---------------------------------------------------------------------------
# run_command — failure exit codes
# ---------------------------------------------------------------------------


class TestRunCommandFailure:
    def test_returns_success_false_on_nonzero_exit(self):
        proc = make_proc(returncode=1, stderr=b"error\n")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.success is False

    def test_appends_stderr_to_stdout_on_failure(self):
        proc = make_proc(returncode=1, stdout=b"partial\n", stderr=b"error\n")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert "partial" in result.data
        assert "error" in result.data

    def test_uses_only_stderr_when_stdout_empty_on_failure(self):
        proc = make_proc(returncode=1, stdout=b"", stderr=b"fatal error\n")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.success is False and result.data == "fatal error\n"

    def test_does_not_append_empty_stderr_on_failure(self):
        proc = make_proc(returncode=1, stdout=b"output\n", stderr=b"")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.success is False and result.data == "output\n"


# ---------------------------------------------------------------------------
# run_command — empty output
# ---------------------------------------------------------------------------


class TestRunCommandEmptyOutput:
    def test_empty_stdout_returns_no_output_placeholder(self):
        proc = make_proc(returncode=0, stdout=b"")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.data == "(no output)"

    def test_whitespace_only_stdout_returns_no_output_placeholder(self):
        proc = make_proc(returncode=0, stdout=b"   \n  ")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.data == "(no output)"

    def test_empty_output_on_zero_exit_is_success(self):
        proc = make_proc(returncode=0, stdout=b"")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.success is True

    def test_empty_output_on_nonzero_exit_is_failure(self):
        proc = make_proc(returncode=1, stdout=b"", stderr=b"")
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.success is False
        assert result.data == "(no output)"


# ---------------------------------------------------------------------------
# run_command — exceptions
# ---------------------------------------------------------------------------


async def _raise_timeout(coro, *args, **kwargs):
    coro.close()
    raise asyncio.TimeoutError()


class TestRunCommandExceptions:
    def test_command_not_found_returns_failure(self):
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            result = asyncio.run(run_command(["nonexistent"]))
        assert result.success is False

    def test_command_not_found_error_contains_command_name(self):
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            result = asyncio.run(run_command(["nonexistent"]))
        assert "nonexistent" in result.error

    def test_command_not_found_error_message_format(self):
        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
            result = asyncio.run(run_command(["nonexistent"]))
        assert "Command not found" in result.error

    def test_timeout_returns_failure(self):
        proc = make_proc()
        with patch_proc(proc):
            with patch("asyncio.wait_for", new=_raise_timeout):
                result = asyncio.run(run_command(["sleep", "100"], timeout=1))
        assert result.success is False

    def test_timeout_error_mentions_timeout_duration(self):
        proc = make_proc()
        with patch_proc(proc):
            with patch("asyncio.wait_for", new=_raise_timeout):
                result = asyncio.run(run_command(["sleep", "100"], timeout=5))
        assert "5s" in result.error

    def test_timeout_kills_process(self):
        proc = make_proc()
        with patch_proc(proc):
            with patch("asyncio.wait_for", new=_raise_timeout):
                asyncio.run(run_command(["sleep", "100"]))
        proc.kill.assert_called_once()

    def test_unexpected_exception_returns_failure(self):
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("permission denied")):
            result = asyncio.run(run_command(["cmd"]))
        assert result.success is False

    def test_unexpected_exception_includes_type_and_message(self):
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("permission denied")):
            result = asyncio.run(run_command(["cmd"]))
        assert "OSError" in result.error
        assert "permission denied" in result.error


# ---------------------------------------------------------------------------
# run_command — truncation
# ---------------------------------------------------------------------------


class TestRunCommandTruncation:
    def test_large_output_is_truncated(self):
        large = ("x" * 80 + "\n") * 700  # well over MAX_CHARS
        proc = make_proc(stdout=large.encode())
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.truncated is True

    def test_truncated_result_has_total_size(self):
        large = ("x" * 80 + "\n") * 700
        proc = make_proc(stdout=large.encode())
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.total_size == len(large)

    def test_truncated_result_has_shown_size(self):
        large = ("x" * 80 + "\n") * 700
        proc = make_proc(stdout=large.encode())
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.shown_size == len(result.data)

    def test_truncated_result_has_hint(self):
        large = ("x" * 80 + "\n") * 700
        proc = make_proc(stdout=large.encode())
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.hint is not None

    def test_output_at_limit_is_not_truncated(self):
        exact = "x" * MAX_CHARS
        proc = make_proc(stdout=exact.encode())
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.truncated is False
        assert result.total_size is None
        assert result.hint is None


# ---------------------------------------------------------------------------
# CmdTool
# ---------------------------------------------------------------------------


class TestCmdTool:
    def test_call_dispatches_to_run_command_with_cmd_output(self):
        tool = GreetTool()
        with patch(
            "ddev.ai.tools.shell.base.run_command", new=AsyncMock(return_value=ToolResult(success=True))
        ) as mock_run:
            asyncio.run(tool.run({"name": "world"}))
        mock_run.assert_called_once_with(["echo", "hello world"], timeout=10)

    def test_default_timeout_is_ten(self):
        assert GreetTool.timeout == 10

    def test_subclass_can_override_timeout(self):
        assert SlowGreetTool.timeout == 60

    def test_overridden_timeout_passed_to_run_command(self):
        tool = SlowGreetTool()
        with patch(
            "ddev.ai.tools.shell.base.run_command", new=AsyncMock(return_value=ToolResult(success=True))
        ) as mock_run:
            asyncio.run(tool.run({"name": "world"}))
        mock_run.assert_called_once_with(["echo", "hello world"], timeout=60)

    def test_cmd_method_is_abstract(self):
        # Cannot instantiate CmdTool without implementing cmd()
        with pytest.raises(TypeError):
            CmdTool()  # type: ignore[abstract]
