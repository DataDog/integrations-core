# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class DdevLintInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name to lint")]
    fmt: Annotated[bool, Field(description="Fix formatting and linting errors instead of only checking")] = False


class DdevLintTool(CmdTool[DdevLintInput]):
    """Runs linter / style checks for the given integration. Set `fmt=true` to
    fix formatting and linting errors instead of only checking them."""

    timeout = 600

    @property
    def name(self) -> str:
        return "ddev_lint"

    def cmd(self, tool_input: DdevLintInput) -> list[str]:
        cmd = ["ddev", "--no-interactive", "test"]
        cmd.append("-fs" if tool_input.fmt else "-s")
        cmd.append(tool_input.integration)
        return cmd
