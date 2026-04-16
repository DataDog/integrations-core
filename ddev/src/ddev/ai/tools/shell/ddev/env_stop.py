# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class EnvStopInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name")]
    environment: Annotated[str, Field(description="Environment name (e.g. py3.11-1.23)")]


class DdevEnvStopTool(CmdTool[EnvStopInput]):
    """Stops and removes the Docker environment for the given integration and environment name."""

    timeout = 120

    @property
    def name(self) -> str:
        return "ddev_env_stop"

    def cmd(self, tool_input: EnvStopInput) -> list[str]:
        return ["ddev", "env", "stop", tool_input.integration, tool_input.environment]
