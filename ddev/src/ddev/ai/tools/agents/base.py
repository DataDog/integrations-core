# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import StopReason
from ddev.ai.tools.core.base import BaseTool, BaseToolInput

if TYPE_CHECKING:
    from ddev.ai.phases.config import AgentConfig
    from ddev.ai.react.factory import ReActProcessFactory

SPAWN_SUBAGENT_NAME = "spawn_subagent"
SPAWN_IDENTICAL_NAME = "spawn_identical_subagents"
MAX_TOKENS_NOTICE = "[SUBAGENT HIT MAX_TOKENS — RESPONSE MAY BE TRUNCATED]"


@dataclass
class ChildOutcome:
    name: str
    text: str | None = None
    stop_reason: StopReason | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


class BaseSpawnTool[TInput: BaseToolInput](BaseTool[TInput]):
    def __init__(
        self,
        owner_id: str,
        agent_config: AgentConfig,
        process_factory: ReActProcessFactory,
    ) -> None:
        self._owner_id = owner_id
        self._agent_config = agent_config
        self._process_factory = process_factory
        # Parent may itself have a spawn tool; never offer either to children.
        self._allowed_tools = set(agent_config.tools) - {SPAWN_SUBAGENT_NAME, SPAWN_IDENTICAL_NAME}

    def _validate_tools(self, tools: list[str], label: str = "Subagent") -> str | None:
        if SPAWN_SUBAGENT_NAME in tools or SPAWN_IDENTICAL_NAME in tools:
            return (
                f"{label!r} not spawned: subagents cannot spawn further subagents "
                f"('{SPAWN_SUBAGENT_NAME}'/'{SPAWN_IDENTICAL_NAME}' are not allowed in 'tools')."
            )
        disallowed = sorted(set(tools) - self._allowed_tools)
        if disallowed:
            return (
                f"{label!r} not spawned: disallowed tools requested: {disallowed}. "
                f"Allowed subset: {sorted(self._allowed_tools)}."
            )
        return None

    async def _run_child(
        self,
        subagent_id: str,
        name: str,
        system_prompt: str,
        prompt: str,
        tools: list[str],
    ) -> ChildOutcome:
        child_scope = AgentScope(owner_id=subagent_id, role=AgentRole.SUBAGENT)
        try:
            child_config = self._agent_config.model_copy(update={"tools": tools})
            process = self._process_factory.create(
                scope=child_scope, agent_config=child_config, system_prompt=system_prompt
            )
        except ValidationError as e:
            return ChildOutcome(name=name, error=f"Invalid child config: {e.error_count()} validation error(s)")
        except Exception as e:
            return ChildOutcome(name=name, error=f"failed to build: {type(e).__name__}: {e}")

        try:
            result = await process.start(prompt)
        except Exception as e:
            return ChildOutcome(name=name, error=f"failed: {type(e).__name__}: {e}")

        text = result.final_response.text
        stop_reason = result.final_response.stop_reason
        if stop_reason == StopReason.MAX_TOKENS:
            text = f"{MAX_TOKENS_NOTICE}\n\n{text}"
        return ChildOutcome(
            name=name,
            text=text,
            stop_reason=stop_reason,
            input_tokens=result.total_input_tokens,
            output_tokens=result.total_output_tokens,
        )
