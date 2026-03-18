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
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    return proc


def patch_proc(proc: MagicMock):
    return patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc))


async def _raise_timeout(coro, *args, **kwargs):
    coro.close()
    raise asyncio.TimeoutError()


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


@pytest.fixture
def proc() -> MagicMock:
    return make_proc(returncode=0, stdout=b"hello\n")


@pytest.fixture
def greet_tool() -> GreetTool:
    return GreetTool()


@pytest.fixture
def slow_greet_tool() -> SlowGreetTool:
    return SlowGreetTool()


# ---------------------------------------------------------------------------
# run_command — output and exit code handling
# ---------------------------------------------------------------------------


def test_run_command_success(proc):
    with patch_proc(proc):
        result = asyncio.run(run_command(["echo", "hello"]))
    assert result.success is True
    assert result.data == "hello\n"
    assert result.truncated is False


def test_run_command_failure_combines_stdout_and_stderr():
    proc = make_proc(returncode=1, stdout=b"partial\n", stderr=b"error\n")
    with patch_proc(proc):
        result = asyncio.run(run_command(["cmd"]))
    assert result.success is False
    assert "partial" in result.data
    assert "error" in result.data


def test_run_command_failure_stderr_only_when_no_stdout():
    proc = make_proc(returncode=1, stdout=b"", stderr=b"fatal error\n")
    with patch_proc(proc):
        result = asyncio.run(run_command(["cmd"]))
    assert result.success is False and result.data == "fatal error\n"


def test_run_command_ignores_stderr_on_zero_exit():
    proc = make_proc(returncode=0, stdout=b"out\n", stderr=b"warning\n")
    with patch_proc(proc):
        result = asyncio.run(run_command(["cmd"]))
    assert result.success is True
    assert "warning" not in result.data


def test_run_command_empty_output():
    for stdout in (b"", b"   \n  "):
        proc = make_proc(returncode=0, stdout=stdout)
        with patch_proc(proc):
            result = asyncio.run(run_command(["cmd"]))
        assert result.data == "(no output)"

    proc = make_proc(returncode=1, stdout=b"", stderr=b"")
    with patch_proc(proc):
        result = asyncio.run(run_command(["cmd"]))
    assert result.success is False and result.data == "(no output)"


# ---------------------------------------------------------------------------
# run_command — exceptions
# ---------------------------------------------------------------------------


def test_run_command_not_found():
    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError()):
        result = asyncio.run(run_command(["nonexistent"]))
    assert result.success is False
    assert "Command not found" in result.error
    assert "nonexistent" in result.error


def test_run_command_timeout():
    proc = make_proc()
    with patch_proc(proc):
        with patch("asyncio.wait_for", new=_raise_timeout):
            result = asyncio.run(run_command(["sleep", "100"], timeout=5))
    assert result.success is False
    assert "5s" in result.error
    proc.kill.assert_called_once()


def test_run_command_unexpected_exception():
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("permission denied")):
        result = asyncio.run(run_command(["cmd"]))
    assert result.success is False
    assert "OSError" in result.error
    assert "permission denied" in result.error


# ---------------------------------------------------------------------------
# run_command — truncation
# ---------------------------------------------------------------------------


def test_run_command_truncation():
    large = ("x" * 80 + "\n") * 700
    proc = make_proc(stdout=large.encode())
    with patch_proc(proc):
        result = asyncio.run(run_command(["cmd"]))
    assert result.truncated is True
    assert result.total_size == len(large)
    assert result.shown_size == len(result.data)
    assert result.hint is not None


def test_run_command_no_truncation_at_limit():
    proc = make_proc(stdout=("x" * MAX_CHARS).encode())
    with patch_proc(proc):
        result = asyncio.run(run_command(["cmd"]))
    assert result.truncated is False
    assert result.total_size is None
    assert result.hint is None


# ---------------------------------------------------------------------------
# CmdTool
# ---------------------------------------------------------------------------


def test_cmd_tool_timeouts(greet_tool: GreetTool, slow_greet_tool: SlowGreetTool):
    assert GreetTool.timeout == 10  # default timeout
    assert SlowGreetTool.timeout == 60  # custom timeout


def test_cmd_tool_dispatches_with_correct_timeout(greet_tool: GreetTool, slow_greet_tool: SlowGreetTool):
    for tool, expected_timeout in [(greet_tool, 10), (slow_greet_tool, 60)]:
        with patch(
            "ddev.ai.tools.shell.base.run_command", new=AsyncMock(return_value=ToolResult(success=True))
        ) as mock_run:
            asyncio.run(tool.run({"name": "world"}))
        mock_run.assert_called_once_with(["echo", "hello world"], timeout=expected_timeout)
