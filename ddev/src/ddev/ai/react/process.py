# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio

from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.exceptions import AgentError
from ddev.ai.agent.scope import AgentScope
from ddev.ai.agent.types import AgentResponse, StopReason, ToolCall, ToolResultMessage
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult

TOOL_RESULTS_SENTINEL = "Tool results"

# A turn that stops on MAX_TOKENS while a tool call is pending was truncated mid-call: the
# tool_use block is incomplete and was never executed. We must still answer every tool_use
# with a tool_result, otherwise the next send() replays a dangling tool_use and the provider
# rejects the request. This synthetic result repairs the conversation and nudges the model
# toward a smaller follow-up. Each tool owns the specifics of that nudge via
# BaseTool.truncated_call_hint; this is only the shared, mechanical part of the message.
TRUNCATED_TOOL_CALL_PREFIX = (
    "This tool call was NOT executed: your previous response was truncated after reaching the "
    "maximum output token limit, so the tool call is incomplete. "
)
GENERIC_TRUNCATED_TOOL_CALL_HINT = "Retry with a smaller, more targeted change."

# Upper bound on back-to-back truncated turns before we give up, to avoid an unrecoverable loop
# where the model keeps emitting an oversized tool call that never fits in the output budget.
MAX_CONSECUTIVE_TRUNCATIONS = 2


class ReActProcess:
    """
    Manages the ReAct (Reason + Act) loop for a single task.

    Sends a prompt to an agent, executes any tool calls in parallel,
    feeds results back, and repeats until the agent stops requesting tools.
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        *,
        scope: AgentScope,
        callbacks: Callbacks | None = None,
        compact_threshold_pct: float | None = 75.0,
    ) -> None:
        """
        Args:
            runtime: Agent runtime containing the agent and its tool registry.
            scope: Identity stamped onto every agent-tier callback event.
            callbacks: Optional Callbacks instance to observe loop events.
            compact_threshold_pct: Context usage percentage at which the loop auto-compacts.
                None disables auto-compaction entirely.
        """
        self._agent = runtime.agent
        self._tool_registry = runtime.tool_registry
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._scope = scope
        self._compact_threshold_pct = compact_threshold_pct

    async def reset(self) -> None:
        """Clear the agent's conversation history."""
        self._agent.reset()
        await self._callbacks.fire_context_cleared(self._scope)

    async def compact(self, response: AgentResponse | None = None) -> tuple[int, int]:
        """Compact the agent's conversation history unconditionally.

        Args:
            response: The last agent response. If None, compaction is unconditional.

        Returns (input_tokens, output_tokens) from the compaction API call.
        Returns (0, 0) if history was already compact and no API call was made.
        """
        await self._callbacks.fire_before_compact(self._scope)

        compact_response = None
        if response is None or not response.tool_calls:
            compact_response = await self._agent.compact()
        else:
            compact_response = await self._agent.compact_preserving_last_turn()

        await self._callbacks.fire_after_compact(self._scope)
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

    async def _execute_tool_calls(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Run all tool calls in parallel, converting any raised exception into a failure result."""
        raw_results = await asyncio.gather(
            *[self._tool_registry.run(tc.name, tc.input) for tc in tool_calls],
            return_exceptions=True,
        )
        return [
            r if isinstance(r, ToolResult) else ToolResult(success=False, error=f"{type(r).__name__}: {r}")
            for r in raw_results
        ]

    def _truncated_tool_results(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Synthetic failure results for a turn truncated by the output token limit.

        Each result carries the specific tool's own recovery hint (BaseTool.truncated_call_hint)
        so the guidance matches what actually broke — e.g. a truncated edit_file and a truncated
        create_file need different follow-ups. Falls back to a generic hint for unknown tools.
        """
        results = []
        for tc in tool_calls:
            tool = self._tool_registry.get(tc.name)
            hint = (tool.truncated_call_hint if tool else None) or GENERIC_TRUNCATED_TOOL_CALL_HINT
            results.append(ToolResult(success=False, error=TRUNCATED_TOOL_CALL_PREFIX + hint))
        return results

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
            tool_names = [d["name"] for d in self._tool_registry.definitions]
            await self._callbacks.fire_agent_start(self._scope, self._agent.system_prompt, tool_names)
            await self._callbacks.fire_before_agent_send(self._scope, prompt, 1)

            response = await self._agent.send(prompt, allowed_tools)
            iterations = 1
            total_input = response.usage.input_tokens
            total_output = response.usage.output_tokens

            await self._callbacks.fire_agent_response(self._scope, response, iterations)

            # No iteration cap — this is an interactive CLI tool; the user can Ctrl+C to stop.
            # Loop while a tool call is pending. A MAX_TOKENS turn can also carry a (truncated)
            # tool_use that must be answered, so we key off tool_calls rather than the stop reason.
            consecutive_truncations = 0
            while response.tool_calls:
                truncated = response.stop_reason == StopReason.MAX_TOKENS
                if truncated:
                    consecutive_truncations += 1
                    if consecutive_truncations > MAX_CONSECUTIVE_TRUNCATIONS:
                        raise AgentError(
                            "Agent response was truncated by the output token limit on "
                            f"{consecutive_truncations} consecutive turns while a tool call was "
                            "pending; aborting to avoid an unrecoverable loop. Reduce the amount "
                            "of work attempted in a single tool call."
                        )
                    tool_results: list[ToolResult] = self._truncated_tool_results(response.tool_calls)
                else:
                    consecutive_truncations = 0
                    tool_results = await self._execute_tool_calls(response.tool_calls)
                total_input += sum(result.total_input_tokens for result in tool_results)
                total_output += sum(result.total_output_tokens for result in tool_results)

                tool_call_results = list(zip(response.tool_calls, tool_results, strict=True))

                for tc, result in tool_call_results:
                    await self._callbacks.fire_tool_call(self._scope, tc, result, iterations)

                messages = [ToolResultMessage(tool_call_id=tc.id, result=result) for tc, result in tool_call_results]

                await self._callbacks.fire_before_agent_send(self._scope, TOOL_RESULTS_SENTINEL, iterations + 1)

                response = await self._agent.send(messages, allowed_tools)
                iterations += 1
                total_input += response.usage.input_tokens
                total_output += response.usage.output_tokens

                await self._callbacks.fire_agent_response(self._scope, response, iterations)

                if self._is_compact_needed(response):
                    compact_in, compact_out = await self.compact(response)
                    total_input += compact_in
                    total_output += compact_out

            if response.stop_reason == StopReason.TOOL_USE:
                raise AgentError("Agent returned stop_reason=TOOL_USE with no tool calls")

            react_result = ReActResult(
                final_response=response,
                iterations=iterations,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                context_usage=response.usage.context_usage,
            )

            await self._callbacks.fire_agent_finish(self._scope, react_result)

            return react_result

        except BaseException as e:
            await self._callbacks.fire_agent_error(self._scope, e)
            raise

    async def run_once(self, prompt: str) -> AgentResponse:
        """Run a single agent turn with no tools available, firing scoped callbacks.
        Does not fire on_agent_start/on_agent_finish callbacks.
        The caller is responsible for token accounting."""
        try:
            await self._callbacks.fire_before_agent_send(self._scope, prompt, 1)
            response = await self._agent.send(prompt, allowed_tools=[])
            await self._callbacks.fire_agent_response(self._scope, response, 1)
            return response
        except BaseException as e:
            await self._callbacks.fire_agent_error(self._scope, e)
            raise
