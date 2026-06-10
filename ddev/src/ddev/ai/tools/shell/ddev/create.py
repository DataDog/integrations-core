# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated, Literal

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool

Platform = Literal["linux", "windows", "mac_os"]


class DdevCreateInput(BaseToolInput):
    integration: Annotated[str, Field(description="Name of the new integration (snake_case)")]
    display_name: Annotated[str, Field(description="Human-readable display name (e.g. 'My Integration')")]
    metrics_prefix: Annotated[str, Field(description="Metric namespace prefix (e.g. 'my_integration.')")]
    platforms: Annotated[
        list[Platform],
        Field(
            description=(
                "Target platforms for the integration. Include all three ('linux', 'windows', 'mac_os') by default;"
                " remove a platform only if the integration explicitly cannot run on it (e.g. a Windows-only service"
                " would omit 'linux' and 'mac_os')."
            ),
            min_length=1,
        ),
    ]


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
            "--display-name",
            tool_input.display_name,
            "--metrics-prefix",
            tool_input.metrics_prefix,
            "--platforms",
            ",".join(tool_input.platforms),
            tool_input.integration,
        ]
