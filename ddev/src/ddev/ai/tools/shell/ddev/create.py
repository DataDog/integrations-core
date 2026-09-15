# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class DdevCreateInput(BaseToolInput):
    integration: Annotated[str, Field(description="Name of the new integration (snake_case)")]


class DdevCreateTool(CmdTool[DdevCreateInput]):
    """Scaffolds a new Datadog Agent check integration with all boilerplate files and
    directory structure. Creates a directory named after the integration (snake_case)
    in the current working directory. Use before writing any integration code."""

    timeout = 60

    @property
    def name(self) -> str:
        return "ddev_create"

    def cmd(self, tool_input: DdevCreateInput) -> list[str]:
        return [
            "ddev",
            "--no-interactive",
            "create",
            "check",
            tool_input.integration,
        ]
