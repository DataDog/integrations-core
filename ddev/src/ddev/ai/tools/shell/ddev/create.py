# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated, Literal

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool

IntegrationType = Literal["check", "check_only", "event", "jmx", "logs", "metrics_crawler", "snmp_tile", "tile"]


class CreateInput(BaseToolInput):
    integration: Annotated[str, Field(description="Name of the new integration (snake_case)")]
    integration_type: Annotated[
        IntegrationType,
        Field(
            description="Template type: 'check' (standard Agent check), 'check_only' (no hatch env),"
            " 'event', 'jmx', 'logs', 'metrics_crawler', 'snmp_tile', 'tile'"
        ),
    ]


class DdevCreateTool(CmdTool[CreateInput]):
    """Scaffolds a new Datadog Agent integration with all boilerplate files and
    directory structure. Use before writing any integration code."""

    timeout = 60

    @property
    def name(self) -> str:
        return "ddev_create"

    def cmd(self, tool_input: CreateInput) -> list[str]:
        return ["ddev", "create", "--type", tool_input.integration_type, "--skip-manifest", tool_input.integration]
