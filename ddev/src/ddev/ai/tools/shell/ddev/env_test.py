# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class EnvTestInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name")]
    environment: Annotated[
        str, Field(description="Environment name (e.g. py3.11-1.23). Defaults to 'all' to test every environment.")
    ] = "all"


class DdevEnvTestTool(CmdTool[EnvTestInput]):
    """Runs E2E tests for an integration. Always passes --dev and tests all environments by default.
    Pass a specific environment name to target a single environment."""

    timeout = 600

    @property
    def name(self) -> str:
        return "ddev_env_test"

    def cmd(self, tool_input: EnvTestInput) -> list[str]:
        return ["ddev", "--no-interactive", "env", "test", "--dev", tool_input.integration, tool_input.environment]
