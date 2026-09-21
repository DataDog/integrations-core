# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class DdevCreateInput(BaseToolInput):
    integration: Annotated[
        str,
        Field(
            description=(
                "Human-readable display name of the new integration, exactly as given "
                "(e.g. 'HPE Aruba Edge'), not a snake_case slug. This command normalizes it "
                "to snake_case for the directory, Python package, and metrics prefix, while "
                "the generated manifest's display-name fields keep it exactly as given."
            )
        ),
    ]


class DdevCreateTool(CmdTool[DdevCreateInput]):
    """Scaffolds a new Datadog Agent check integration with all boilerplate files and
    directory structure. Use before writing any integration code."""

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
