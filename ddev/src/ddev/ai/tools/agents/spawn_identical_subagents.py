# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import asyncio
from typing import Annotated

from pydantic import Field

from ddev.ai.agent.types import StopReason
from ddev.ai.tools.agents.base import SPAWN_IDENTICAL_NAME, BaseSpawnTool, ChildOutcome
from ddev.ai.tools.core.base import BaseToolInput
from ddev.ai.tools.core.types import ToolResult

DEFAULT_PARALLEL = 8
MAX_ASSIGNMENTS = 32
CONCISE_DIRECTIVE = (
    "Keep your final answer as concise as possible: report only the essential result, with no preamble "
    "or restating of the task. Your output is aggregated with many sibling subagents', so verbosity "
    "risks overflowing the parent's context."
)


class Assignment(BaseToolInput):
    name: Annotated[
        str,
        Field(description="Short label, unique within the call.", pattern=r"^[A-Za-z0-9._-]{1,64}$"),
    ]
    prompt: Annotated[
        str,
        Field(description="This child's user turn."),
    ]


class SpawnIdenticalSubagentsInput(BaseToolInput):
    system_prompt: Annotated[
        str,
        Field(
            description="Shared system prompt used verbatim for every child. Put the role and common instructions here."
        ),
    ]
    tools: Annotated[
        list[str],
        Field(description="Tool subset granted to every child. Must be a subset of your tools; no spawn tool allowed."),
    ] = []
    assignments: Annotated[
        list[Assignment],
        Field(
            description="One entry per child. Keep each prompt small — only the assignment-specific part.", min_length=1
        ),
    ]
    max_parallel: Annotated[
        int | None,
        Field(description="Optional cap on concurrent children.", ge=1),
    ] = None


class SpawnIdenticalSubagentsTool(BaseSpawnTool[SpawnIdenticalSubagentsInput]):
    """Run the SAME subagent (identical system prompt and tools) over many different assignments.

    Prefer this over issuing several 'spawn_subagent' calls when the children share a role: the shared
    system prompt and tool set are sent once, not repeated per child, saving output tokens. Each child
    differs only by its short assignment prompt — e.g. renaming metrics where each child handles one
    batch of metric families. Children run in parallel; results come back in assignment order and one
    failing child never affects its siblings."""

    @property
    def name(self) -> str:
        return SPAWN_IDENTICAL_NAME

    async def __call__(self, tool_input: SpawnIdenticalSubagentsInput) -> ToolResult:
        names = [a.name for a in tool_input.assignments]
        if len(set(names)) != len(names):
            return ToolResult(success=False, error="Assignment names must be unique.")
        if len(tool_input.assignments) > MAX_ASSIGNMENTS:
            return ToolResult(
                success=False, error=f"Too many assignments: {len(tool_input.assignments)} > {MAX_ASSIGNMENTS}."
            )
        if error := self._validate_tools(tool_input.tools, "parallel"):
            return ToolResult(success=False, error=error)

        limit = tool_input.max_parallel or min(len(tool_input.assignments), DEFAULT_PARALLEL)
        semaphore = asyncio.Semaphore(limit)
        system_prompt = f"{tool_input.system_prompt}\n\n{CONCISE_DIRECTIVE}"

        async def run(index: int, assignment: Assignment) -> ChildOutcome:
            async with semaphore:
                subagent_id = f"{self._owner_id}.par.{index:03d}-{assignment.name}"
                return await self._run_child(
                    subagent_id, assignment.name, system_prompt, assignment.prompt, tool_input.tools
                )

        results = await asyncio.gather(
            *(run(i, a) for i, a in enumerate(tool_input.assignments)), return_exceptions=True
        )

        outcomes: list[ChildOutcome] = []
        for assignment, result in zip(tool_input.assignments, results, strict=True):
            if isinstance(result, BaseException):
                outcomes.append(ChildOutcome(name=assignment.name, error=f"failed: {type(result).__name__}: {result}"))
            else:
                outcomes.append(result)

        sections = "\n\n".join(self._format(o) for o in outcomes)
        return ToolResult(
            success=any(o.error is None for o in outcomes),
            data=sections,
            error=None if any(o.error is None for o in outcomes) else "All children failed.",
            total_input_tokens=sum(o.input_tokens for o in outcomes),
            total_output_tokens=sum(o.output_tokens for o in outcomes),
        )

    def _format(self, outcome: ChildOutcome) -> str:
        if outcome.error is not None:
            return f"## {outcome.name} — FAILED: {outcome.error}"
        status = "TRUNCATED (max_tokens)" if outcome.stop_reason == StopReason.MAX_TOKENS else "ok"
        return f"## {outcome.name} — {status}\n{outcome.text}"
