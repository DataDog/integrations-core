# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class EnvTestInput(BaseToolInput):
    integration: Annotated[str, Field(description="Integration name")]
    environment: Annotated[str, Field(description="Environment name (e.g. py3.11-1.23)")]
    dev: Annotated[bool, Field(description="Pass --dev flag (use if env was started with --dev)")] = False


class DdevEnvTestTool(CmdTool[EnvTestInput]):
    """Runs E2E tests for the given integration in the specified environment.
    `ddev env test` starts the environment, runs the tests, and stops it automatically —
    no prior `ddev_env_start` is needed. Use `dev=true` to pass the `--dev` flag."""

    timeout = 600

    @property
    def name(self) -> str:
        return "ddev_env_test"

    def cmd(self, tool_input: EnvTestInput) -> list[str]:
        cmd = ["ddev", "--no-interactive", "env", "test"]
        if tool_input.dev:
            cmd.append("--dev")
        cmd += [tool_input.integration, tool_input.environment]
        return cmd
