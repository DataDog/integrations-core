# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from ddev.ai.agent.types import (
    AgentConnectionError,
    AgentResponse,
    ContextUsage,
    StopReason,
    TokenUsage,
    ToolCall,
)
from ddev.ai.react.process import ReActCallback, ReActProcess, ReActResult, TerminationReason
from ddev.ai.tools.core.types import ToolResult

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockAgent:
    """Minimal AgentProtocol implementation that replays a fixed list of responses."""

    def __init__(self, responses: list[AgentResponse]) -> None:
        self._responses = iter(responses)
        self.send_calls: list = []

    async def send(self, content, allowed_tools=None) -> AgentResponse:
        self.send_calls.append(content)
        return next(self._responses)

    def reset(self) -> None:
        pass


class MockToolRegistry:
    """Minimal tool registry that always returns a configurable ToolResult."""

    def __init__(self, result: ToolResult | None = None) -> None:
        self._result = result or ToolResult(success=True, data="ok")
        self.run_calls: list[tuple[str, dict]] = []

    async def run(self, name: str, raw: dict[str, object]) -> ToolResult:
        self.run_calls.append((name, raw))
        return self._result


class MockCallback:
    """Records all lifecycle events emitted by ReActProcess."""

    def __init__(self) -> None:
        self.agent_responses: list[tuple[AgentResponse, int]] = []
        self.tool_calls_seen: list[tuple[ToolCall, ToolResult, int]] = []
        self.complete_results: list[ReActResult] = []
        self.errors: list[Exception] = []

    async def on_agent_response(self, response: AgentResponse, iteration: int) -> None:
        self.agent_responses.append((response, iteration))

    async def on_tool_call(self, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        self.tool_calls_seen.append((tool_call, result, iteration))

    async def on_complete(self, result: ReActResult) -> None:
        self.complete_results.append(result)

    async def on_error(self, error: Exception) -> None:
        self.errors.append(error)


def make_response(
    stop_reason: StopReason,
    tool_calls: list[ToolCall] | None = None,
    input_tokens: int = 10,
    output_tokens: int = 5,
    context_usage: ContextUsage | None = None,
) -> AgentResponse:
    return AgentResponse(
        stop_reason=stop_reason,
        text="",
        tool_calls=tool_calls or [],
        usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            context_usage=context_usage,
        ),
    )


def make_tool_call(id: str = "tc_01", name: str = "read_file", input: dict | None = None) -> ToolCall:
    return ToolCall(id=id, name=name, input=input or {})


def make_process(
    agent: MockAgent,
    registry: MockToolRegistry | None = None,
    max_iterations: int = 10,
    callbacks: list[ReActCallback] | None = None,
) -> ReActProcess:
    return ReActProcess(
        agent=agent,
        tool_registry=registry or MockToolRegistry(),
        max_iterations=max_iterations,
        callbacks=callbacks,
    )


# ---------------------------------------------------------------------------
# Termination reasons — parametrized single-response cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stop_reason,expected_termination",
    [
        (StopReason.END_TURN, TerminationReason.END_TURN),
        (StopReason.MAX_TOKENS, TerminationReason.MAX_TOKENS),
        (StopReason.OTHER, TerminationReason.END_TURN),  # OTHER maps to END_TURN
    ],
)
async def test_termination_reason_single_response(stop_reason, expected_termination) -> None:
    agent = MockAgent([make_response(stop_reason)])

    result = await make_process(agent).start("Hi")

    assert result.termination_reason == expected_termination
    assert result.iterations == 1
    assert len(agent.send_calls) == 1


# ---------------------------------------------------------------------------
# Single tool call
# ---------------------------------------------------------------------------


async def test_single_tool_call_executes_tool_and_returns() -> None:
    tc = make_tool_call("tc_01", "read_file")
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[tc]),
        make_response(StopReason.END_TURN),
    ]
    registry = MockToolRegistry()
    agent = MockAgent(responses)

    result = await make_process(agent, registry=registry).start("Do something")

    assert result.termination_reason == TerminationReason.END_TURN
    assert result.iterations == 2
    assert len(registry.run_calls) == 1
    assert registry.run_calls[0][0] == "read_file"
    assert len(agent.send_calls) == 2
    assert isinstance(agent.send_calls[1], list)
    assert agent.send_calls[1][0].tool_call_id == "tc_01"


# ---------------------------------------------------------------------------
# Multi-tool parallel dispatch
# ---------------------------------------------------------------------------


async def test_multi_tool_parallel_dispatches_all() -> None:
    tool_calls = [
        make_tool_call("tc_01", "a"),
        make_tool_call("tc_02", "b"),
        make_tool_call("tc_03", "c"),
    ]
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=tool_calls),
        make_response(StopReason.END_TURN),
    ]
    registry = MockToolRegistry()
    agent = MockAgent(responses)

    await make_process(agent, registry=registry).start("Do three things")

    assert len(registry.run_calls) == 3
    assert {name for name, _ in registry.run_calls} == {"a", "b", "c"}
    assert len(agent.send_calls[1]) == 3


# ---------------------------------------------------------------------------
# Max iterations guard
# ---------------------------------------------------------------------------


async def test_max_iterations_terminates_loop() -> None:
    # Agent always returns TOOL_USE — loop must be capped at max_iterations=3
    responses = [make_response(StopReason.TOOL_USE, tool_calls=[make_tool_call()])] * 10
    agent = MockAgent(responses)

    result = await make_process(agent, max_iterations=3).start("Loop forever")

    assert result.termination_reason == TerminationReason.MAX_ITERATIONS
    assert result.iterations == 3
    assert len(agent.send_calls) == 3  # initial + 2 tool-result rounds


# ---------------------------------------------------------------------------
# Callbacks fired correctly
# ---------------------------------------------------------------------------


async def test_callbacks_invoked_correct_counts() -> None:
    tool_calls = [make_tool_call("tc_01"), make_tool_call("tc_02", "grep")]
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=tool_calls),
        make_response(StopReason.END_TURN),
    ]
    callback = MockCallback()
    agent = MockAgent(responses)

    result = await make_process(agent, callbacks=[callback]).start("Run tools")

    assert len(callback.agent_responses) == 2
    assert callback.agent_responses[0][1] == 1
    assert callback.agent_responses[1][1] == 2
    assert len(callback.tool_calls_seen) == 2
    assert all(iteration == 1 for _, _, iteration in callback.tool_calls_seen)
    assert len(callback.complete_results) == 1
    assert callback.complete_results[0] is result
    assert len(callback.errors) == 0


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------


class ErrorAgent:
    async def send(self, content, allowed_tools=None) -> AgentResponse:
        raise AgentConnectionError("network down")

    def reset(self) -> None:
        pass


async def test_agent_error_notifies_and_reraises() -> None:
    callback = MockCallback()
    process = ReActProcess(
        agent=ErrorAgent(),
        tool_registry=MockToolRegistry(),
        callbacks=[callback],
    )

    with pytest.raises(AgentConnectionError):
        await process.start("Anything")

    assert len(callback.errors) == 1
    assert isinstance(callback.errors[0], AgentConnectionError)
    assert len(callback.complete_results) == 0
    assert len(callback.agent_responses) == 0


# ---------------------------------------------------------------------------
# Token accumulation
# ---------------------------------------------------------------------------


async def test_total_tokens_summed_across_iterations() -> None:
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[make_tool_call()], input_tokens=100, output_tokens=50),
        make_response(StopReason.END_TURN, input_tokens=200, output_tokens=80),
    ]
    agent = MockAgent(responses)

    result = await make_process(agent).start("Task")

    assert result.total_input_tokens == 300
    assert result.total_output_tokens == 130
    assert result.iterations == 2


# ---------------------------------------------------------------------------
# Context usage propagation — parametrized None vs present
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "context_usage",
    [
        None,
        ContextUsage(window_size=200_000, used_tokens=50_000),
    ],
)
async def test_context_usage_propagated(context_usage: ContextUsage | None) -> None:
    agent = MockAgent([make_response(StopReason.END_TURN, context_usage=context_usage)])

    result = await make_process(agent).start("Hi")

    assert result.context_usage is context_usage
    assert result.final_response.usage.context_usage is context_usage
