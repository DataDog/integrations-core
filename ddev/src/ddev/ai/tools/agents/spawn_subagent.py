# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from ddev.ai.agent.types import StopReason
from ddev.ai.react.process import ReActProcess
from ddev.ai.tools.agents.agent_logger import AgentLogger
from ddev.ai.tools.core.base import BaseTool, BaseToolInput
from ddev.ai.tools.core.types import ToolResult

if TYPE_CHECKING:
    from ddev.ai.agent.build import AgentRuntimeBuilder
    from ddev.ai.phases.config import AgentConfig


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


class SpawnSubagentTool(BaseTool[SpawnSubagentInput]):
    """Delegate a self-contained subtask to a fresh subagent.

    The subagent runs one Reason-Action loop with the provided system prompt, user prompt, and tool subset.
    Only the subagent's final assistant message is returned to you. Instruct the subagent in your prompt
    to put anything you need in its final message. Include every piece of context the subagent needs
    inside the system prompt and the user prompt."""

    def __init__(
        self,
        owner_id: str,
        agent_config: AgentConfig,
        runtime_builder: AgentRuntimeBuilder,
        log_dir: Path,
    ) -> None:
        self._owner_id = owner_id
        self._agent_config = agent_config
        self._runtime_builder = runtime_builder
        # Parent may itself have spawn_subagent; never offer it to children.
        self._allowed_tools = set(agent_config.tools) - {self.name}
        self._log_dir = log_dir
        self._counter = 0

    @property
    def name(self) -> str:
        return "spawn_subagent"

    def _label(self, tool_input: SpawnSubagentInput) -> str:
        return tool_input.name or "unnamed"

    async def __call__(self, tool_input: SpawnSubagentInput) -> ToolResult:
        label = self._label(tool_input)

        # Subset validation — return failed ToolResult; no log file is opened.
        if self.name in tool_input.tools:
            return ToolResult(
                success=False,
                error=(
                    f"Subagent {label!r} not spawned: subagents cannot spawn further subagents "
                    f"('{self.name}' is not allowed in 'tools')."
                ),
            )
        disallowed = sorted(set(tool_input.tools) - self._allowed_tools)
        if disallowed:
            return ToolResult(
                success=False,
                error=(
                    f"Subagent {label!r} not spawned: disallowed tools requested: {disallowed}. "
                    f"Allowed subset: {sorted(self._allowed_tools)}."
                ),
            )

        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return ToolResult(
                success=False,
                error=(f"Subagent {label!r} not spawned: cannot create log directory {self._log_dir}: {e}"),
            )

        self._counter += 1
        subagent_id = f"{self._owner_id}.sub.{self._counter:03d}-{label}"
        log_path = self._log_dir / f"{self._counter:03d}-{label}.jsonl"

        try:
            logger = AgentLogger(log_path)
        except OSError as e:
            return ToolResult(
                success=False,
                error=f"Subagent {label!r} not spawned: cannot open log file {log_path}: {e}",
            )

        try:
            logger.log_start(
                system_prompt=tool_input.system_prompt,
                prompt=tool_input.prompt,
                tools=tool_input.tools,
            )

            try:
                child_config = self._agent_config.model_copy(update={"tools": tool_input.tools})
                runtime = self._runtime_builder(
                    agent_config=child_config,
                    system_prompt=tool_input.system_prompt,
                    owner_id=subagent_id,
                )
            except Exception as e:
                logger.log_finish(success=False, error=f"build failed: {type(e).__name__}: {e}")
                return ToolResult(
                    success=False,
                    error=f"Subagent {label!r} failed to build: {type(e).__name__}: {e}",
                )

            process = ReActProcess(
                runtime,
                callbacks=logger.build_callbacks(),
            )
            try:
                result = await process.start(tool_input.prompt)
            except Exception as e:
                logger.log_finish(success=False, error=f"{type(e).__name__}: {e}")
                return ToolResult(
                    success=False,
                    error=f"Subagent {label!r} failed: {type(e).__name__}: {e}",
                )

            logger.log_finish(
                success=True,
                iterations=result.iterations,
                total_input_tokens=result.total_input_tokens,
                total_output_tokens=result.total_output_tokens,
                stop_reason=str(result.final_response.stop_reason),
            )

            data = result.final_response.text
            if result.final_response.stop_reason == StopReason.MAX_TOKENS:
                data = "[SUBAGENT HIT MAX_TOKENS — RESPONSE MAY BE TRUNCATED]\n\n" + data
            return ToolResult(
                success=True,
                data=data,
                total_input_tokens=result.total_input_tokens,
                total_output_tokens=result.total_output_tokens,
            )
        finally:
            logger.close()
