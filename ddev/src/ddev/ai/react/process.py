# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.exceptions import AgentError
from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, ToolCall, ToolResultMessage
from ddev.ai.tools.core.registry import ToolRegistry
from ddev.ai.tools.core.types import ToolResult


@dataclass(frozen=True)
class ReActResult:
    """Immutable summary of a completed ReAct loop run."""

    final_response: AgentResponse
    iterations: int
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

    async def on_error(self, error: BaseException) -> None:
        """Called when the loop aborts — covers AgentError, KeyboardInterrupt, and CancelledError.
        The exception is always re-raised after this returns."""
        ...


class ReActProcess:
    """
    Manages the ReAct (Reason + Act) loop for a single task.

    Sends a prompt to an agent, executes any tool calls in parallel,
    feeds results back, and repeats until the agent stops requesting tools.
    """

    def __init__(
        self,
        agent: BaseAgent[Any],
        tool_registry: ToolRegistry,
        callbacks: list[ReActCallback] | None = None,
    ) -> None:
        """
        Args:
            agent: A BaseAgent subclass (e.g. AnthropicAgent).
            tool_registry: Registry of tools available in this loop.
            callbacks: Optional observers. Empty list means no events are fired.
        """
        self._agent = agent
        self._tool_registry = tool_registry
        self._callbacks: list[ReActCallback] = callbacks or []

    async def start(self, prompt: str, allowed_tools: list[str] | None = None) -> ReActResult:
        """
        Run the ReAct loop for a single task.

        Args:
            prompt: The initial user prompt to send to the agent.
            allowed_tools: Optional subset of tools the agent may call in this run. None means all.

        Returns:
            A ReActResult summarising the final response, token counts, and iteration count.

        Raises:
            Every exception is forwarded after notifying callbacks.
        """
        try:
            response = await self._agent.send(prompt, allowed_tools)
            iterations = 1
            total_input = response.usage.input_tokens
            total_output = response.usage.output_tokens

            for cb in self._callbacks:
                try:
                    await cb.on_agent_response(response, iterations)
                except Exception:
                    pass  # in the future we should log this error

            # No iteration cap — this is an interactive CLI tool; the user can Ctrl+C to stop.
            while response.stop_reason == StopReason.TOOL_USE:
                if not response.tool_calls:
                    raise AgentError("Agent returned stop_reason=TOOL_USE with no tool calls")

                raw_results = await asyncio.gather(
                    *[self._tool_registry.run(tc.name, tc.input) for tc in response.tool_calls],
                    return_exceptions=True,
                )
                tool_results: list[ToolResult] = [
                    r if isinstance(r, ToolResult) else ToolResult(success=False, error=f"{type(r).__name__}: {r}")
                    for r in raw_results
                ]

                tool_call_results = list(zip(response.tool_calls, tool_results, strict=True))

                for tc, result in tool_call_results:
                    for cb in self._callbacks:
                        try:
                            await cb.on_tool_call(tc, result, iterations)
                        except Exception:
                            pass

                messages = [ToolResultMessage(tool_call_id=tc.id, result=result) for tc, result in tool_call_results]

                response = await self._agent.send(messages, allowed_tools)
                iterations += 1
                total_input += response.usage.input_tokens
                total_output += response.usage.output_tokens

                for cb in self._callbacks:
                    try:
                        await cb.on_agent_response(response, iterations)
                    except Exception:
                        pass

            react_result = ReActResult(
                final_response=response,
                iterations=iterations,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                context_usage=response.usage.context_usage,
            )

            for cb in self._callbacks:
                try:
                    await cb.on_complete(react_result)
                except Exception:
                    pass

            return react_result

        except BaseException as e:
            for cb in self._callbacks:
                try:
                    await cb.on_error(e)
                except Exception:
                    pass
            raise
