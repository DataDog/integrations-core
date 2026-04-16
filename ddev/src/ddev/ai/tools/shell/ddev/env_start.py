# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class EnvStartInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name")]
    environment: Annotated[str, Field(description="Environment name (e.g. py3.11-1.23)")]
    dev: Annotated[bool, Field(description="Mount local check code into the container")] = False


class DdevEnvStartTool(CmdTool[EnvStartInput]):
    """Starts a Docker-based E2E test environment for an integration. Use
    `dev=true` to mount local check code into the container."""

    timeout = 300

    @property
    def name(self) -> str:
        return "ddev_env_start"

    def cmd(self, tool_input: EnvStartInput) -> list[str]:
        cmd = ["ddev", "--no-interactive", "env", "start"]
        if tool_input.dev:
            cmd.append("--dev")
        cmd += [tool_input.integration, tool_input.environment]
        return cmd
