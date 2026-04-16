# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class DdevTestInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name to test")]
    lint: Annotated[bool, Field(description="Run linter / style checks only (-s / --lint)")] = False
    fmt: Annotated[bool, Field(description="Fix formatting and linting errors (-fs / --fmt)")] = False
    pytest_args: Annotated[
        list[str] | None,
        Field(description='Extra pytest arguments passed after `--` (e.g. ["-k", "test_my_func", "-s"])'),
    ] = None


class DdevTestTool(CmdTool[DdevTestInput]):
    """Runs unit and integration tests for the given integration. Set `lint=true`
    to run the linter only. Set `fmt=true` to fix formatting and linting errors.
    Use `pytest_args` to pass extra pytest arguments (e.g. `["-k", "test_my_func"]`)
    to run specific tests instead of the full suite."""

    timeout = 600

    @property
    def name(self) -> str:
        return "ddev_test"

    def cmd(self, tool_input: DdevTestInput) -> list[str]:
        cmd = ["ddev", "--no-interactive", "test"]
        if tool_input.lint:
            cmd.append("-s")
        if tool_input.fmt:
            cmd.append("-fs")
        cmd.append(tool_input.integration)
        if tool_input.pytest_args:
            cmd += ["--"] + tool_input.pytest_args
        return cmd
