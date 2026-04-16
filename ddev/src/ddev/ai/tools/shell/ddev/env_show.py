# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class EnvShowInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name")]


class DdevEnvShowTool(CmdTool[EnvShowInput]):
    """Lists all available E2E environment names for an integration. Call this
    before `ddev_env_test` or `ddev_env_start` to discover valid environment names."""

    timeout = 30

    @property
    def name(self) -> str:
        return "ddev_env_show"

    def cmd(self, tool_input: EnvShowInput) -> list[str]:
        return ["ddev", "--no-interactive", "env", "show", tool_input.integration]
