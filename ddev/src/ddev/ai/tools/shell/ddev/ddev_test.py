# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class DdevTestInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name to test")]
    pytest_args: Annotated[
        list[str] | None,
        Field(description='Extra pytest arguments passed after `--` (e.g. ["-k", "test_my_func", "-s"])'),
    ] = None


class DdevTestTool(CmdTool[DdevTestInput]):
    """Runs unit and integration tests for the given integration. Use `pytest_args`
    to pass extra pytest arguments (e.g. `["-k", "test_my_func"]`) to run specific
    tests instead of the full suite."""

    timeout = 600

    @property
    def name(self) -> str:
        return "ddev_test"

    def cmd(self, tool_input: DdevTestInput) -> list[str]:
        cmd = ["ddev", "--no-interactive", "test", tool_input.integration]
        if tool_input.pytest_args:
            cmd += ["--"] + tool_input.pytest_args
        return cmd
