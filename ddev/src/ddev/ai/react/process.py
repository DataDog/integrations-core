# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from ddev.ai.agent.types import (
    AgentError,
    AgentProtocol,
    AgentResponse,
    ContextUsage,
    StopReason,
    ToolCall,
    ToolResultMessage,
)
from ddev.ai.tools.core.registry import ToolRegistry
from ddev.ai.tools.core.types import ToolResult


class TerminationReason(StrEnum):
    """Describes why a ReActProcess loop stopped."""

    END_TURN = "end_turn"
    MAX_ITERATIONS = "max_iterations"
    MAX_TOKENS = "max_tokens"


@dataclass(frozen=True)
class ReActResult:
    """Immutable summary of a completed ReAct loop run."""

    final_response: AgentResponse  # if MAX_ITERATIONS, tool_calls here were requested but not executed
    iterations: int
    termination_reason: TerminationReason
    total_input_tokens: int  # sum across all iterations
    total_output_tokens: int  # sum across all iterations
    context_usage: ContextUsage | None  # promoted from final_response.usage.context_usage


class ReActCallback(Protocol):
    """Observer interface for ReActProcess lifecycle events."""

    async def on_agent_response(self, response: AgentResponse, iteration: int) -> None:
        """Called after every agent.send() returns, including the first."""
        ...

    async def on_tool_call(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        """Called once per (tool_call, result) pair after all tools in a batch execute."""
        ...

    async def on_complete(self, result: ReActResult) -> None:
        """Called when the loop exits cleanly with a ReActResult."""
        ...

    async def on_error(self, error: Exception) -> None:
        """Called when an AgentError is raised. The exception is re-raised after this returns."""
        ...


def _derive_termination_reason(
    stop_reason: StopReason,
    iterations: int,
    max_iterations: int,
) -> TerminationReason:
    """Map loop exit state to a TerminationReason."""
    if stop_reason == StopReason.TOOL_USE and iterations >= max_iterations:
        return TerminationReason.MAX_ITERATIONS
    if stop_reason == StopReason.MAX_TOKENS:
        return TerminationReason.MAX_TOKENS
    # StopReason.OTHER (refusal, stop_sequence) maps to END_TURN by design.
    # Callers needing the distinction can inspect result.final_response.stop_reason.
    return TerminationReason.END_TURN


class ReActProcess:
    """
    Manages the ReAct (Reason + Act) loop for a single task.

    Sends a prompt to an agent, executes any tool calls in parallel,
    feeds results back, and repeats until the agent stops requesting
    tools or a guard condition is reached.
    """

    def __init__(
        self,
        agent: AgentProtocol,
        tool_registry: ToolRegistry,
        max_iterations: int = 50,
        callbacks: list[ReActCallback] | None = None,
    ) -> None:
        """
        Args:
            agent: Satisfies AgentProtocol (e.g. AnthropicAgent).
            tool_registry: Registry of tools available in this loop.
            max_iterations: Safety cap — loop exits with MAX_ITERATIONS if hit.
            callbacks: Optional observers. Empty list means no events are fired.
        """
        self._agent = agent
        self._tool_registry = tool_registry
        self._max_iterations = max_iterations
        self._callbacks: list[ReActCallback] = callbacks or []

    async def start(self, prompt: str, allowed_tools: list[str] | None = None) -> ReActResult:
        """
        Run the ReAct loop for a single task.

        Args:
            prompt: The initial user prompt to send to the agent.
            allowed_tools: Optional subset of tools the agent may call in this run. None means all.

        Returns:
            A ReActResult summarising the final response, token counts,
            iteration count, and termination reason.

        Raises:
            AgentError: Any error from the agent is forwarded after notifying callbacks.
        """
        try:
            response = await self._agent.send(prompt, allowed_tools)
            iterations = 1
            total_input = response.usage.input_tokens
            total_output = response.usage.output_tokens

            for cb in self._callbacks:
                await cb.on_agent_response(response, iterations)

            while response.stop_reason == StopReason.TOOL_USE and iterations < self._max_iterations:
                if not response.tool_calls:
                    raise AgentError("Agent returned stop_reason=TOOL_USE with no tool calls")

                raw_results = await asyncio.gather(
                    *[self._tool_registry.run(tc.name, tc.input) for tc in response.tool_calls],
                    return_exceptions=True,
                )
                tool_results: list[ToolResult] = [
                    r if isinstance(r, ToolResult) else ToolResult(success=False, error=str(r)) for r in raw_results
                ]

                tool_call_results = list(zip(response.tool_calls, tool_results, strict=True))

                for tc, result in tool_call_results:
                    for cb in self._callbacks:
                        await cb.on_tool_call(tc, result, iterations)

                messages = [ToolResultMessage(tool_call_id=tc.id, result=result) for tc, result in tool_call_results]

                response = await self._agent.send(messages, allowed_tools)
                iterations += 1
                total_input += response.usage.input_tokens
                total_output += response.usage.output_tokens

                for cb in self._callbacks:
                    await cb.on_agent_response(response, iterations)

            termination = _derive_termination_reason(response.stop_reason, iterations, self._max_iterations)
            react_result = ReActResult(
                final_response=response,
                iterations=iterations,
                termination_reason=termination,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                context_usage=response.usage.context_usage,
            )

            for cb in self._callbacks:
                await cb.on_complete(react_result)

            return react_result

        except AgentError as e:
            for cb in self._callbacks:
                try:
                    await cb.on_error(e)
                except Exception:
                    pass
            raise
