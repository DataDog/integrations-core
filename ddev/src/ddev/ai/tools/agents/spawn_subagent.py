# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ddev.ai.tools.agents.base import SPAWN_SUBAGENT_NAME, BaseSpawnTool
from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult


class SpawnSubagentInput(BaseToolInput):
    system_prompt: Annotated[
        str,
        Field(description="System prompt that defines the subagent's role and behavior."),
    ]
    prompt: Annotated[
        str,
        Field(description="The task prompt sent to the subagent as its first (and only) user turn."),
    ]
    tools: Annotated[
        list[str],
        Field(
            description=(
                "Names of tools the subagent may use. Must be a subset of your tool list and "
                "may not include 'spawn_subagent'. May be empty if the subagent should answer "
                "from the prompt alone."
            ),
        ),
    ] = []
    name: Annotated[
        str | None,
        Field(
            description=("Optional short human-readable name for the subagent."),
            pattern=r"^$|^[A-Za-z0-9._-]{1,64}$",
        ),
    ] = None


class SpawnSubagentTool(BaseSpawnTool[SpawnSubagentInput]):
    """Delegate a self-contained subtask to a fresh subagent.

    The subagent runs one Reason-Action loop with the provided system prompt, user prompt, and tool subset.
    Only the subagent's final assistant message is returned to you. Instruct the subagent in your prompt
    to put anything you need in its final message. Include every piece of context the subagent needs
    inside the system prompt and the user prompt."""

    def __init__(self, owner_id, agent_config, process_factory) -> None:
        super().__init__(owner_id, agent_config, process_factory)
        self._counter = 0

    @property
    def name(self) -> str:
        return SPAWN_SUBAGENT_NAME

    async def __call__(self, tool_input: SpawnSubagentInput) -> ToolResult:
        label = tool_input.name or "unnamed"

        if error := self._validate_tools(tool_input.tools, label):
            return ToolResult(success=False, error=error)

        self._counter += 1
        subagent_id = f"{self._owner_id}.sub.{self._counter:03d}-{label}"
        outcome = await self._run_child(
            subagent_id, label, tool_input.system_prompt, tool_input.prompt, tool_input.tools
        )
        if outcome.error is not None:
            return ToolResult(success=False, error=f"Subagent {label!r} {outcome.error}")
        return ToolResult(
            success=True,
            data=outcome.text,
            total_input_tokens=outcome.input_tokens,
            total_output_tokens=outcome.output_tokens,
        )
