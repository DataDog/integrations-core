# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated, Literal

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool

ValidateSubcommand = Literal["config", "models", "metadata"]


class DdevValidateInput(BaseToolInput):
    subcommand: Annotated[
        ValidateSubcommand,
        Field(
            description=(
                "Which validator to run. "
                "'config' validates assets/configuration/spec.yaml against data/conf.yaml.example. "
                "'models' validates spec.yaml against datadog_checks/<integration>/config_models/. "
                "'metadata' validates metadata.csv. "
            )
        ),
    ]
    integration: Annotated[str, Field(description="Integration name to validate")]
    sync: Annotated[
        bool,
        Field(
            description=(
                "Regenerate / auto-fix derived files instead of only checking. "
                "For 'config', regenerates conf.yaml.example. "
                "For 'models', regenerates config_models/. "
                "For 'metadata', rewrites metadata.csv into canonical form. "
            )
        ),
    ] = False


_SYNC_FLAG: dict[ValidateSubcommand, str] = {
    "config": "-s",
    "models": "-s",
    "metadata": "--sync",
}


class DdevValidateTool(CmdTool[DdevValidateInput]):
    """Validates an integration's spec, config example, config models, or metadata.csv.
    Set `sync=true` to regenerate the derived files from spec.yaml."""

    timeout = 120

    @property
    def name(self) -> str:
        return "ddev_validate"

    def cmd(self, tool_input: DdevValidateInput) -> list[str]:
        cmd = ["ddev", "--no-interactive", "validate", tool_input.subcommand]
        if tool_input.sync:
            cmd.append(_SYNC_FLAG[tool_input.subcommand])
        cmd.append(tool_input.integration)
        return cmd
