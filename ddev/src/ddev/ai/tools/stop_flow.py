# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Annotated

from pydantic import Field

from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult


class StopFlowInput(BaseToolInput):
    reason: Annotated[
        str,
        Field(
            description=(
                "Precise explanation of what makes the current task impossible to complete as "
                "specified, so a human can fix the instructions and rerun. For example: 'the PRD "
                "requires connecting to an endpoint that does not exist'."
            )
        ),
    ]


class StopFlowTool(BaseTool[StopFlowInput]):
    """Stop the entire run immediately because the task cannot be completed as specified.

    Use this only when the described goal is actually unreachable — e.g. the instructions require
    something that does not exist or contradicts itself — not for an obstacle you can work around
    or retry. This ends the whole run, not just the current phase or subagent, so a human can fix
    the instructions and run again. Explain precisely what is blocking completion."""

    @property
    def name(self) -> str:
        return "stop_flow"

    async def __call__(self, tool_input: StopFlowInput) -> ToolResult:
        return ToolResult(success=True, data=f"Stop requested: {tool_input.reason}", stop_reason=tool_input.reason)
