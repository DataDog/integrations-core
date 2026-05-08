# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated, Literal

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class DdevValidateInput(BaseToolInput):
    subcommand: Annotated[
        Literal["config", "models", "metadata", "all"],
        Field(
            description=(
                "Which validator to run. "
                "'config' validates assets/configuration/spec.yaml against data/conf.yaml.example. "
                "'models' validates spec.yaml against datadog_checks/<integration>/config_models/. "
                "'metadata' validates metadata.csv. "
                "'all' runs the full orchestrator across every validator."
            )
        ),
    ]
    integration: Annotated[str, Field(description="Integration name to validate")]
    sync: Annotated[
        bool,
        Field(
            description=(
                "Regenerate / auto-fix derived files instead of only checking. "
                "For 'config' and 'models', regenerates conf.yaml.example and config_models/ from spec.yaml. "
                "For 'metadata', rewrites metadata.csv into canonical form. "
                "For 'all', forwards an auto-fix flag to every sub-validator that supports it."
            )
        ),
    ] = False


# Maps the user-facing `sync` boolean to the actual CLI flag the underlying
# `ddev validate <subcommand>` accepts.
_SYNC_FLAG: dict[str, str] = {
    "config": "-s",
    "models": "-s",
    "metadata": "--sync",
    "all": "--fix",
}


class DdevValidateTool(CmdTool[DdevValidateInput]):
    """Validates an integration's spec, generated config example, generated
    Pydantic config models, or metadata.csv. Set `sync=true` to regenerate the
    derived files (conf.yaml.example, config_models/, metadata.csv) from the
    spec, instead of only checking them. Always run with `sync=true` after
    editing assets/configuration/spec.yaml so the generated files stay in sync."""

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
