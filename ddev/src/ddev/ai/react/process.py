# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from typing import Any

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.exceptions import AgentError
from ddev.ai.agent.types import AgentResponse, StopReason, ToolResultMessage
from ddev.ai.react.callbacks import CallbackSet
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.registry import ToolRegistry


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
        callback_sets: list[CallbackSet] | None = None,
        compact_threshold_pct: float | None = 75.0,
    ) -> None:
        """
        Args:
            agent: A BaseAgent subclass (e.g. AnthropicAgent).
            tool_registry: Registry of tools available in this loop.
            callback_sets: Optional CallbackSet instances to observe loop events.
            compact_threshold_pct: Context usage percentage at which the loop auto-compacts.
                None disables auto-compaction entirely.
        """
        self._agent = agent
        self._tool_registry = tool_registry
        self._callback_sets: list[CallbackSet] = callback_sets or []
        self._compact_threshold_pct = compact_threshold_pct

    def reset(self) -> None:
        """Clear the agent's conversation history."""
        self._agent.reset()

    async def compact(self, response: AgentResponse | None = None) -> tuple[int, int]:
        """Compact the agent's conversation history unconditionally.

        Args:
            response: The last agent response. If None, compaction is unconditional.

        Returns (input_tokens, output_tokens) from the compaction API call.
        Returns (0, 0) if history was already compact and no API call was made.
        """
        for cb_set in self._callback_sets:
            await cb_set.fire_before_compact()

        compact_response = None
        if response is None or response.stop_reason != StopReason.TOOL_USE:
            compact_response = await self._agent.compact()
        else:
            compact_response = await self._agent.compact_preserving_last_turn()

        for cb_set in self._callback_sets:
            await cb_set.fire_after_compact()
        if compact_response is None:
            return 0, 0
        return compact_response.usage.input_tokens, compact_response.usage.output_tokens

    def _is_compact_needed(self, response: AgentResponse) -> bool:
        if self._compact_threshold_pct is None:
            return False
        ctx = response.usage.context_usage
        if ctx is None or ctx.context_pct < self._compact_threshold_pct:
            return False
        return True

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
            for cb_set in self._callback_sets:
                await cb_set.fire_before_agent_send(1)

            response = await self._agent.send(prompt, allowed_tools)
            iterations = 1
            total_input = response.usage.input_tokens
            total_output = response.usage.output_tokens

            for cb_set in self._callback_sets:
                await cb_set.fire_agent_response(response, iterations)

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
                    for cb_set in self._callback_sets:
                        await cb_set.fire_tool_call(tc, result, iterations)

                messages = [ToolResultMessage(tool_call_id=tc.id, result=result) for tc, result in tool_call_results]

                for cb_set in self._callback_sets:
                    await cb_set.fire_before_agent_send(iterations + 1)

                response = await self._agent.send(messages, allowed_tools)
                iterations += 1
                total_input += response.usage.input_tokens
                total_output += response.usage.output_tokens

                for cb_set in self._callback_sets:
                    await cb_set.fire_agent_response(response, iterations)

                if self._is_compact_needed(response):
                    compact_in, compact_out = await self.compact(response)
                    total_input += compact_in
                    total_output += compact_out

            react_result = ReActResult(
                final_response=response,
                iterations=iterations,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                context_usage=response.usage.context_usage,
            )

            for cb_set in self._callback_sets:
                await cb_set.fire_complete(react_result)

            return react_result

        except BaseException as e:
            for cb_set in self._callback_sets:
                await cb_set.fire_error(e)
            raise
