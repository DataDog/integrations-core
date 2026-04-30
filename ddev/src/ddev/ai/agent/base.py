# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Final

from ddev.ai.agent.types import AgentResponse, ToolResultMessage
from ddev.ai.tools.registry import ToolRegistry

_COMPACT_SYSTEM_PROMPT: Final[str] = """\
You are summarizing an agentic conversation to free up context space.
Produce a dense, structured summary that covers ALL of the following:
  1. The original task given to the agent
  2. Every tool call made and the key finding or result from each
  3. Any decisions, conclusions, or hypotheses the agent reached
  4. What has been completed and what work remains

Rules:
- Be exhaustive on facts and findings; omit raw data already consumed
- Use bullet points, not prose
- The agent will read ONLY this summary to continue — it must be self-sufficient
"""

_COMPACT_REQUEST: Final[str] = "Summarize the conversation so far following your instructions."


class BaseAgent[TMessage](ABC):
    """Abstract base class for all agent implementations.

    Provides shared, provider-agnostic history management and compaction.
    The message type TMessage is supplied by each concrete provider
    (e.g. MessageParam for Anthropic). Subclasses must implement send().
    """

    def __init__(self, name: str, system_prompt: str, tools: ToolRegistry) -> None:
        self._history: list[TMessage] = []
        self.name = name
        self._system_prompt = system_prompt
        self._tools = tools

    @property
    def history(self) -> list[TMessage]:
        """Read-only snapshot of the conversation history."""
        return deepcopy(self._history)

    def reset(self) -> None:
        """Clear conversation history to start a new conversation."""
        self._history = []

    async def compact(self) -> AgentResponse | None:
        """Collapse history to 2 messages: original task + LLM summary.

        Returns the AgentResponse from the compaction call so callers can
        account for its token usage. Returns None if history is already ≤ 2.
        """
        if len(self._history) <= 2:
            return None

        original_prompt = self._history[0]
        original_system = self._system_prompt

        self._system_prompt = _COMPACT_SYSTEM_PROMPT
        try:
            response = await self.send(_COMPACT_REQUEST, allowed_tools=[])
        finally:
            self._system_prompt = original_system  # restore even if send() raises

        compact_response = self._history[-1]  # summary message added by send()

        self.reset()
        self._history = [original_prompt, compact_response]
        return response

    async def compact_preserving_last_turn(self) -> AgentResponse | None:
        """Compact history while keeping the last user+assistant pair intact.

        Used mid-ReAct loop where the last assistant message contains unresolved
        tool calls that still need a tool-result response. After compaction the
        preserved pair re-anchors the pending turn so the next send(tool_results)
        produces a valid alternating message sequence. No-op if history is ≤ 3
        messages (too short to compact without corrupting the sequence).

        Returns the AgentResponse from the compaction call, or None if no
        compaction occurred.
        """
        if len(self._history) <= 3:
            return None

        last_turn = self._history[-2:]  # [user(tool_results_N), assistant(tool_use_N+1)]
        response = await self.compact()
        self._history.extend(last_turn)
        return response

    @abstractmethod
    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse: ...
