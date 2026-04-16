# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class TestInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name to test")]
    fmt: Annotated[bool, Field(description="Run code formatter (ruff format)")] = False
    style: Annotated[bool, Field(description="Run linter / style checks (ruff check)")] = False


class DdevTestTool(CmdTool[TestInput]):
    """Runs unit and integration tests for the given integration. Set `fmt=true`
    to auto-format code, `style=true` to run the linter. Use `fmt=true, style=true` together
    to do both."""

    timeout = 600

    @property
    def name(self) -> str:
        return "ddev_test"

    def cmd(self, tool_input: TestInput) -> list[str]:
        cmd = ["ddev", "--no-interactive", "test"]
        if tool_input.fmt and tool_input.style:
            cmd.append("-fs")
        elif tool_input.fmt:
            cmd.append("-f")
        elif tool_input.style:
            cmd.append("-s")
        cmd.append(tool_input.integration)
        return cmd
