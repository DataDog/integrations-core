# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated, Literal

from pydantic import Field

from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.shell.base import CmdTool


class ReleaseChangelogInput(BaseToolInput):
    change_type: Annotated[
        Literal["fixed", "added", "changed"],
        Field(description="Type of change: 'fixed' (patch), 'added' (minor), 'changed' (major)"),
    ]
    integration: Annotated[str, Field(description="Integration name")]
    message: Annotated[str, Field(description="Human-readable changelog message")]


class DdevReleaseChangelogTool(CmdTool[ReleaseChangelogInput]):
    """Creates a changelog entry file for the integration. `change_type` must be
    `"fixed"` (patch bump), `"added"` (minor bump), or `"changed"` (major bump)."""

    timeout = 30

    @property
    def name(self) -> str:
        return "ddev_release_changelog"

    def cmd(self, tool_input: ReleaseChangelogInput) -> list[str]:
        return [
            "ddev",
            "release",
            "changelog",
            "new",
            tool_input.change_type,
            tool_input.integration,
            "-m",
            tool_input.message,
        ]
