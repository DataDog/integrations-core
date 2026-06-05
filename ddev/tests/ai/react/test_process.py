# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from typing import Any

import pytest

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.exceptions import AgentConnectionError
from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, TokenUsage, ToolCall, ToolResultMessage
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.react.process import ReActProcess
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult
from ddev.ai.tools.registry import ToolRegistry

_TOOL_RESULT_DATA: str = "ok"

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class MockAgent(BaseAgent[Any]):
    """Minimal BaseAgent implementation that replays a fixed list of responses."""

    def __init__(self, responses: list[AgentResponse]) -> None:
        super().__init__(name="mock", system_prompt="", tools=ToolRegistry([]))
        self._responses = iter(responses)
        self.send_calls: list[str | list[ToolResultMessage]] = []
        self.compact_calls: int = 0
        self.compact_preserving_turn_calls: int = 0
        self.compact_response: AgentResponse | None = None
        self.compact_token_response: AgentResponse | None = None
        self.reset_calls: int = 0

    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        self.send_calls.append(content)
        return next(self._responses)

    async def compact(self) -> AgentResponse | None:
        self.compact_calls += 1
        return self.compact_response

    async def compact_preserving_last_turn(self) -> AgentResponse | None:
        self.compact_preserving_turn_calls += 1
        return self.compact_token_response

    def reset(self) -> None:
        super().reset()
        self.reset_calls += 1


class MockToolRegistry:
    """Minimal tool registry that always returns a configurable ToolResult."""

    def __init__(self, result: ToolResult | None = None) -> None:
        self._result = result or ToolResult(success=True, data=_TOOL_RESULT_DATA)
        self.run_calls: list[tuple[str, dict]] = []

    @property
    def definitions(self) -> list[dict]:
        return []

    async def run(self, name: str, raw: dict[str, object]) -> ToolResult:
        self.run_calls.append((name, raw))
        return self._result


class RaisingToolRegistry:
    """Registry that always raises a given exception from run()."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.run_calls: list[tuple[str, dict]] = []

    @property
    def definitions(self) -> list[dict]:
        return []

    async def run(self, name: str, raw: dict[str, object]) -> ToolResult:
        self.run_calls.append((name, raw))
        raise self._exc


class PerToolRegistry:
    """Registry that dispatches per tool name, raising or returning per configured behavior."""

    def __init__(self, behaviors: dict[str, ToolResult | BaseException]) -> None:
        self._behaviors = behaviors
        self.run_calls: list[tuple[str, dict]] = []

    @property
    def definitions(self) -> list[dict]:
        return []

    async def run(self, name: str, raw: dict[str, object]) -> ToolResult:
        self.run_calls.append((name, raw))
        behavior = self._behaviors[name]
        if isinstance(behavior, BaseException):
            raise behavior
        return behavior


class CallbackRecorder:
    """Test helper that wires a CallbackSet to record all lifecycle events."""

    def __init__(self) -> None:
        self.agent_starts: list[tuple[AgentScope, str, list[str]]] = []
        self.before_sends: list[tuple[str, int]] = []
        self.agent_responses: list[tuple[AgentResponse, int]] = []
        self.tool_calls_seen: list[tuple[AgentScope, ToolCall, ToolResult, int]] = []
        self.complete_results: list[ReActResult] = []
        self.errors: list[BaseException] = []
        self.before_compacts: int = 0
        self.after_compacts: int = 0

        self.callback_set = CallbackSet()

        @self.callback_set.on_agent_start
        async def _record_start(scope: AgentScope, system_prompt: str, tools: list[str]) -> None:
            self.agent_starts.append((scope, system_prompt, tools))

        @self.callback_set.on_before_agent_send
        async def _record_before_send(scope: AgentScope, prompt: str, iteration: int) -> None:
            self.before_sends.append((prompt, iteration))

        @self.callback_set.on_agent_response
        async def _record_response(scope: AgentScope, response: AgentResponse, iteration: int) -> None:
            self.agent_responses.append((response, iteration))

        @self.callback_set.on_tool_call
        async def _record_tool_call(scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
            self.tool_calls_seen.append((scope, tool_call, result, iteration))

        @self.callback_set.on_agent_finish
        async def _record_complete(scope: AgentScope, result: ReActResult) -> None:
            self.complete_results.append(result)

        @self.callback_set.on_agent_error
        async def _record_error(scope: AgentScope, error: BaseException) -> None:
            self.errors.append(error)

        @self.callback_set.on_before_compact
        async def _record_before_compact(scope: AgentScope) -> None:
            self.before_compacts += 1

        @self.callback_set.on_after_compact
        async def _record_after_compact(scope: AgentScope) -> None:
            self.after_compacts += 1


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


def make_tool_call(
    call_id: str = "tc_01", name: str = "read_file", tool_input: dict[str, Any] | None = None
) -> ToolCall:
    return ToolCall(id=call_id, name=name, input=tool_input or {})


def make_process(
    agent: MockAgent,
    registry: MockToolRegistry | None = None,
    callbacks: Callbacks | None = None,
    compact_threshold_pct: float | None = None,
    scope: AgentScope | None = None,
) -> ReActProcess:
    return ReActProcess(
        AgentRuntime(agent=agent, tool_registry=registry or MockToolRegistry()),
        callbacks=callbacks,
        scope=scope or AgentScope(owner_id="test", role=AgentRole.PHASE),
        compact_threshold_pct=compact_threshold_pct,
    )


# ---------------------------------------------------------------------------
# Stop reasons — parametrized single-response cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stop_reason", [StopReason.END_TURN, StopReason.MAX_TOKENS, StopReason.OTHER])
async def test_stop_reason_single_response(stop_reason: StopReason) -> None:
    agent = MockAgent([make_response(stop_reason)])

    result = await make_process(agent).start("Hi")

    assert result.final_response.stop_reason == stop_reason
    assert result.iterations == 1
    assert len(agent.send_calls) == 1
    assert agent.send_calls[0] == "Hi"


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

    assert result.final_response.stop_reason == StopReason.END_TURN
    assert result.iterations == 2
    assert len(registry.run_calls) == 1
    assert registry.run_calls[0][0] == "read_file"
    assert len(agent.send_calls) == 2
    assert agent.send_calls[0] == "Do something"
    assert isinstance(agent.send_calls[1], list)
    assert agent.send_calls[1][0].tool_call_id == "tc_01"
    assert agent.send_calls[1][0].result.data == _TOOL_RESULT_DATA


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
# Tool exception resilience
# ---------------------------------------------------------------------------


async def test_tool_exception_loop_continues_with_failure_result() -> None:
    """(a) A raising tool must not abort the loop. (b) Its ToolResultMessage must have success=False."""
    tc = make_tool_call("tc_01", "read_file")
    agent = MockAgent(
        [
            make_response(StopReason.TOOL_USE, tool_calls=[tc]),
            make_response(StopReason.END_TURN),
        ]
    )

    result = await make_process(agent, registry=RaisingToolRegistry(RuntimeError("disk error"))).start("Do something")

    assert result.iterations == 2
    assert result.final_response.stop_reason == StopReason.END_TURN
    sent_back = agent.send_calls[1]
    assert isinstance(sent_back, list)
    assert sent_back[0].result.success is False


async def test_tool_exception_on_tool_call_callback_fires_with_error_result() -> None:
    """(c) on_tool_call must fire even when the tool raised, carrying the failure ToolResult."""
    tc = make_tool_call("tc_01", "read_file")
    agent = MockAgent(
        [
            make_response(StopReason.TOOL_USE, tool_calls=[tc]),
            make_response(StopReason.END_TURN),
        ]
    )
    recorder = CallbackRecorder()

    await make_process(
        agent,
        registry=RaisingToolRegistry(ValueError("oops")),
        callbacks=Callbacks([recorder.callback_set]),
    ).start("x")

    assert len(recorder.tool_calls_seen) == 1
    _, _, error_result, _ = recorder.tool_calls_seen[0]
    assert error_result.success is False


@pytest.mark.parametrize(
    "exc,expected_error",
    [
        (RuntimeError("disk error"), "RuntimeError: disk error"),
        (ValueError("bad input"), "ValueError: bad input"),
        (OSError("file not found"), "OSError: file not found"),
    ],
)
async def test_tool_exception_error_message_format(exc: BaseException, expected_error: str) -> None:
    """Error string in the failure result must be formatted as 'ExceptionType: message'."""
    tc = make_tool_call()
    agent = MockAgent(
        [
            make_response(StopReason.TOOL_USE, tool_calls=[tc]),
            make_response(StopReason.END_TURN),
        ]
    )

    await make_process(agent, registry=RaisingToolRegistry(exc)).start("x")

    sent_back: list[ToolResultMessage] = agent.send_calls[1]
    assert sent_back[0].result.error == expected_error


async def test_partial_batch_failure_only_affects_raising_tool() -> None:
    """In a multi-tool batch, only the raising tool gets success=False; successful tools are unaffected."""
    tc_ok = make_tool_call("tc_01", "read_file")
    tc_bad = make_tool_call("tc_02", "write_file")
    agent = MockAgent(
        [
            make_response(StopReason.TOOL_USE, tool_calls=[tc_ok, tc_bad]),
            make_response(StopReason.END_TURN),
        ]
    )
    registry = PerToolRegistry(
        {
            "read_file": ToolResult(success=True, data="contents"),
            "write_file": RuntimeError("permission denied"),
        }
    )

    result = await make_process(agent, registry=registry).start("Do both")

    assert result.iterations == 2
    sent_back: list[ToolResultMessage] = agent.send_calls[1]
    assert len(sent_back) == 2
    results = {msg.tool_call_id: msg.result for msg in sent_back}
    assert results["tc_01"].success is True
    assert results["tc_01"].data == "contents"
    assert results["tc_02"].success is False
    assert "RuntimeError" in (results["tc_02"].error or "")


# ---------------------------------------------------------------------------
# Callbacks fired correctly
# ---------------------------------------------------------------------------


async def test_callbacks_invoked_correct_counts() -> None:
    tool_calls = [make_tool_call("tc_01"), make_tool_call("tc_02", "grep")]
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=tool_calls),
        make_response(StopReason.END_TURN),
    ]
    expected_result = ToolResult(success=True, data="ok")
    registry = MockToolRegistry(result=expected_result)
    recorder = CallbackRecorder()
    agent = MockAgent(responses)
    scope = AgentScope(owner_id="owner-loop", role=AgentRole.SUBAGENT)

    result = await make_process(
        agent, registry=registry, callbacks=Callbacks([recorder.callback_set]), scope=scope
    ).start("Run tools")

    assert len(recorder.agent_responses) == 2
    assert recorder.agent_responses[0][1] == 1
    assert recorder.agent_responses[1][1] == 2
    assert len(recorder.tool_calls_seen) == 2
    assert all(iteration == 1 for *_, iteration in recorder.tool_calls_seen)
    # In-loop callbacks must carry the process's scope, not a default or stale one.
    assert all(seen_scope is scope for seen_scope, *_ in recorder.tool_calls_seen)
    assert recorder.tool_calls_seen[0][1] is tool_calls[0]
    assert recorder.tool_calls_seen[1][1] is tool_calls[1]
    assert recorder.tool_calls_seen[0][2] is expected_result
    assert recorder.tool_calls_seen[1][2] is expected_result
    assert len(recorder.complete_results) == 1
    assert recorder.complete_results[0] is result
    assert len(recorder.errors) == 0


async def test_two_callback_sets_both_notified() -> None:
    agent = MockAgent([make_response(StopReason.END_TURN)])
    rec_a, rec_b = CallbackRecorder(), CallbackRecorder()
    await make_process(agent, callbacks=Callbacks([rec_a.callback_set, rec_b.callback_set])).start("x")
    assert len(rec_a.complete_results) == 1
    assert len(rec_b.complete_results) == 1


async def test_agent_start_fires_first_with_scope_and_metadata() -> None:
    agent = MockAgent([make_response(StopReason.END_TURN)])
    agent._system_prompt = "you are a tester"
    recorder = CallbackRecorder()
    scope = AgentScope(owner_id="owner-1", role=AgentRole.SUBAGENT)

    await make_process(agent, callbacks=Callbacks([recorder.callback_set]), scope=scope).start("do it")

    assert len(recorder.agent_starts) == 1
    fired_scope, system_prompt, tools = recorder.agent_starts[0]
    assert fired_scope is scope
    assert system_prompt == "you are a tester"
    assert tools == []
    assert recorder.before_sends[0] == ("do it", 1)


# ---------------------------------------------------------------------------
# run_once — single no-tools turn
# ---------------------------------------------------------------------------


async def test_run_once_sends_with_no_tools_and_fires_scoped_callbacks() -> None:
    agent = MockAgent([make_response(StopReason.END_TURN, input_tokens=7, output_tokens=3)])
    recorder = CallbackRecorder()
    scope = AgentScope(owner_id="owner-1", role=AgentRole.PHASE)

    process = make_process(agent, callbacks=Callbacks([recorder.callback_set]), scope=scope)
    response = await process.run_once("summarize")

    assert response.usage.input_tokens == 7
    assert agent.send_calls == ["summarize"]
    # run_once is a single turn: one before_send, one response, no agent_start/finish.
    assert len(recorder.agent_responses) == 1
    assert recorder.agent_responses[0][1] == 1
    assert recorder.before_sends == [("summarize", 1)]
    assert recorder.agent_starts == []
    assert recorder.complete_results == []


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------


class ErrorAgent(BaseAgent[Any]):
    def __init__(self) -> None:
        super().__init__(name="error", system_prompt="", tools=ToolRegistry([]))

    async def send(
        self, content: str | list[ToolResultMessage], allowed_tools: list[str] | None = None
    ) -> AgentResponse:
        raise AgentConnectionError("network down")


async def test_agent_error_notifies_and_reraises() -> None:
    recorder = CallbackRecorder()
    process = ReActProcess(
        AgentRuntime(agent=ErrorAgent(), tool_registry=MockToolRegistry()),
        scope=AgentScope(owner_id="test", role=AgentRole.PHASE),
        callbacks=Callbacks([recorder.callback_set]),
    )

    with pytest.raises(AgentConnectionError):
        await process.start("Anything")

    assert len(recorder.errors) == 1
    assert isinstance(recorder.errors[0], AgentConnectionError)
    assert len(recorder.complete_results) == 0
    assert len(recorder.agent_responses) == 0


class InterruptAgent(BaseAgent[Any]):
    def __init__(self) -> None:
        super().__init__(name="interrupt", system_prompt="", tools=ToolRegistry([]))

    async def send(
        self, content: str | list[ToolResultMessage], allowed_tools: list[str] | None = None
    ) -> AgentResponse:
        raise KeyboardInterrupt


async def test_keyboard_interrupt_notifies_and_reraises() -> None:
    recorder = CallbackRecorder()
    process = ReActProcess(
        AgentRuntime(agent=InterruptAgent(), tool_registry=MockToolRegistry()),
        scope=AgentScope(owner_id="test", role=AgentRole.PHASE),
        callbacks=Callbacks([recorder.callback_set]),
    )

    with pytest.raises(KeyboardInterrupt):
        await process.start("Anything")

    assert len(recorder.errors) == 1
    assert isinstance(recorder.errors[0], KeyboardInterrupt)
    assert len(recorder.complete_results) == 0


class CancelledAgent(BaseAgent[Any]):
    def __init__(self) -> None:
        super().__init__(name="cancelled", system_prompt="", tools=ToolRegistry([]))

    async def send(
        self, content: str | list[ToolResultMessage], allowed_tools: list[str] | None = None
    ) -> AgentResponse:
        raise asyncio.CancelledError


async def test_cancelled_error_notifies_and_reraises() -> None:
    recorder = CallbackRecorder()
    process = ReActProcess(
        AgentRuntime(agent=CancelledAgent(), tool_registry=MockToolRegistry()),
        scope=AgentScope(owner_id="test", role=AgentRole.PHASE),
        callbacks=Callbacks([recorder.callback_set]),
    )

    with pytest.raises(asyncio.CancelledError):
        await process.start("Anything")

    assert len(recorder.errors) == 1
    assert isinstance(recorder.errors[0], asyncio.CancelledError)
    assert len(recorder.complete_results) == 0


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


async def test_tool_result_tokens_included_in_total_tokens() -> None:
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[make_tool_call()], input_tokens=100, output_tokens=50),
        make_response(StopReason.END_TURN, input_tokens=200, output_tokens=80),
    ]
    agent = MockAgent(responses)
    registry = MockToolRegistry(ToolResult(success=True, data="ok", total_input_tokens=30, total_output_tokens=10))

    result = await make_process(agent, registry=registry).start("Task")

    assert result.total_input_tokens == 330
    assert result.total_output_tokens == 140


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


# ---------------------------------------------------------------------------
# reset() and compact() — delegation
# ---------------------------------------------------------------------------


async def test_reset_delegates_to_agent() -> None:
    agent = MockAgent([])
    make_process(agent).reset()
    assert agent.reset_calls == 1
    assert agent.history == []


async def test_compact_delegates_to_agent_returns_zero_when_no_op() -> None:
    agent = MockAgent([])  # compact_response is None — no compaction occurred
    compact_in, compact_out = await make_process(agent).compact()
    assert agent.compact_calls == 1
    assert compact_in == 0
    assert compact_out == 0


async def test_compact_returns_tokens_when_compaction_occurs() -> None:
    agent = MockAgent([])
    agent.compact_response = make_response(StopReason.END_TURN, input_tokens=40, output_tokens=15)
    compact_in, compact_out = await make_process(agent).compact()
    assert compact_in == 40
    assert compact_out == 15


async def test_compact_fires_before_and_after_callbacks() -> None:
    agent = MockAgent([])
    recorder = CallbackRecorder()
    await make_process(agent, callbacks=Callbacks([recorder.callback_set])).compact()
    assert recorder.before_compacts == 1
    assert recorder.after_compacts == 1


# ---------------------------------------------------------------------------
# Auto-compact inside the ReAct loop
# ---------------------------------------------------------------------------


def make_context_usage(pct: float, window: int = 200_000) -> ContextUsage:
    return ContextUsage(window_size=window, used_tokens=int(window * pct / 100))


async def test_auto_compact_triggers_when_threshold_exceeded() -> None:
    tc = make_tool_call()
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[tc]),
        make_response(StopReason.END_TURN, context_usage=make_context_usage(80.0)),
    ]
    agent = MockAgent(responses)
    await make_process(agent, compact_threshold_pct=75.0).start("task")
    assert agent.compact_calls == 1


async def test_auto_compact_fires_callbacks() -> None:
    tc = make_tool_call()
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[tc]),
        make_response(StopReason.END_TURN, context_usage=make_context_usage(80.0)),
    ]
    agent = MockAgent(responses)
    recorder = CallbackRecorder()
    await make_process(agent, callbacks=Callbacks([recorder.callback_set]), compact_threshold_pct=75.0).start("task")
    assert recorder.before_compacts == 1
    assert recorder.after_compacts == 1


async def test_auto_compact_does_not_trigger_below_threshold() -> None:
    tc = make_tool_call()
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[tc]),
        make_response(StopReason.END_TURN, context_usage=make_context_usage(50.0)),
    ]
    agent = MockAgent(responses)
    await make_process(agent, compact_threshold_pct=75.0).start("task")
    assert agent.compact_preserving_turn_calls == 0


async def test_auto_compact_disabled_when_threshold_is_none() -> None:
    tc = make_tool_call()
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[tc]),
        make_response(StopReason.END_TURN, context_usage=make_context_usage(99.9)),
    ]
    agent = MockAgent(responses)
    await make_process(agent, compact_threshold_pct=None).start("task")
    assert agent.compact_preserving_turn_calls == 0


async def test_auto_compact_skipped_when_context_usage_is_none() -> None:
    tc = make_tool_call()
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[tc]),
        make_response(StopReason.END_TURN, context_usage=None),
    ]
    agent = MockAgent(responses)
    await make_process(agent, compact_threshold_pct=75.0).start("task")
    assert agent.compact_preserving_turn_calls == 0


async def test_auto_compact_tokens_included_in_result() -> None:
    tc = make_tool_call()
    responses = [
        make_response(StopReason.TOOL_USE, tool_calls=[tc], input_tokens=100, output_tokens=50),
        make_response(StopReason.END_TURN, context_usage=make_context_usage(80.0), input_tokens=200, output_tokens=80),
    ]
    agent = MockAgent(responses)
    agent.compact_response = make_response(StopReason.END_TURN, input_tokens=30, output_tokens=10)

    result = await make_process(agent, compact_threshold_pct=75.0).start("task")

    assert result.total_input_tokens == 100 + 200 + 30
    assert result.total_output_tokens == 50 + 80 + 10
