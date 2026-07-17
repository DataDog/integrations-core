# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import json
from pathlib import Path

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.agent.types import (
    AgentResponse,
    StopReason,
    TokenUsage,
    ToolCall,
    WebActivity,
    WebCitation,
    WebFetchCall,
    WebSearchCall,
)
from ddev.ai.react.types import ReActResult
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.tools.core.types import ToolResult


def make_response(text: str = "", stop_reason: StopReason = StopReason.END_TURN) -> AgentResponse:
    return AgentResponse(
        stop_reason=stop_reason,
        text=text,
        tool_calls=[],
        usage=TokenUsage(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


def make_result(response: AgentResponse | None = None) -> ReActResult:
    response = response or make_response()
    return ReActResult(
        final_response=response,
        iterations=2,
        total_input_tokens=30,
        total_output_tokens=12,
        context_usage=None,
    )


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


PHASE = AgentScope(owner_id="p1", role=AgentRole.PHASE, phase_id="p1")
SUB = AgentScope(owner_id="p1.sub.001-x", role=AgentRole.SUBAGENT, phase_id="p1")


async def test_demultiplexes_by_scope_into_separate_files(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_agent_start(PHASE, "sys", [])
    await cb.fire_agent_start(SUB, "sys2", ["read_file"])

    phase_path = tmp_path / "phase" / "p1.jsonl"
    sub_path = tmp_path / "subagent" / "p1.sub.001-x.jsonl"
    assert phase_path.exists()
    assert sub_path.exists()
    assert read_events(phase_path)[0]["system_prompt"] == "sys"
    assert read_events(sub_path)[0]["tools"] == ["read_file"]


async def test_full_sequence_writes_start_and_finish_with_timestamps(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_agent_start(PHASE, "sys", ["read_file"])
    await cb.fire_before_agent_send(PHASE, "do", 1)
    await cb.fire_agent_response(PHASE, make_response("hi"), 1)
    await cb.fire_tool_call(PHASE, ToolCall(id="t1", name="read_file", input={}), ToolResult(success=True, data="x"), 1)
    await cb.fire_agent_finish(PHASE, make_result())

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    assert [e["event"] for e in events] == ["start", "before_agent_send", "agent_response", "tool_call", "finish"]
    assert events[1]["prompt"] == "do"
    assert all("ts" in e for e in events)
    assert events[-1]["success"] is True
    assert events[-1]["iterations"] == 2


async def test_error_emits_error_then_failed_finish(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_agent_start(PHASE, "sys", [])
    await cb.fire_agent_error(PHASE, ValueError("boom"))

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    names = [e["event"] for e in events]
    assert names == ["start", "error", "finish"]
    assert "ValueError: boom" in events[1]["exception"]
    assert events[2]["success"] is False


async def test_timeout_cancellation_has_meaningful_error(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_agent_error(PHASE, asyncio.CancelledError("Orchestrator exceeded max_timeout of 10s"))

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    assert events[0]["exception"] == "Timed out: Orchestrator exceeded max_timeout of 10s"
    assert events[1]["error"] == "Timed out: Orchestrator exceeded max_timeout of 10s"


async def test_compact_events_recorded(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_before_compact(PHASE)
    await cb.fire_after_compact(PHASE)

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    assert [e["event"] for e in events] == ["before_compact", "after_compact"]


async def test_context_cleared_event_recorded(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_context_cleared(PHASE)

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    assert [e["event"] for e in events] == ["context_cleared"]


async def test_reused_scope_appends_to_same_file(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_before_agent_send(PHASE, "first", 1)
    await cb.fire_before_agent_send(PHASE, "second", 2)

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    assert [e["prompt"] for e in events] == ["first", "second"]


async def test_close_is_idempotent(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()
    await cb.fire_agent_start(PHASE, "sys", [])

    logger.close()
    logger.close()  # must not raise


async def test_emit_after_close_is_silently_dropped(tmp_path):
    logger = AgentLogger(tmp_path)
    scope = AgentScope(owner_id="p1", role=AgentRole.PHASE, phase_id="p1")
    logger.close()
    cb = logger.as_callback_set()
    await cb.fire_agent_start(scope, "sys", [])
    assert not (tmp_path / AgentRole.PHASE.value / "p1.jsonl").exists()


async def test_agent_response_logs_web_searches_and_citations(tmp_path):
    activity = WebActivity(
        searches=[WebSearchCall(query="python typing", result_count=5)],
        citations=[WebCitation(url="https://docs.python.org", cited_text="PEP 484", title="PEP 484")],
    )
    response = AgentResponse(
        stop_reason=StopReason.END_TURN,
        text="here",
        tool_calls=[],
        usage=TokenUsage(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
        web_activity=activity,
    )
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_agent_response(PHASE, response, 1)

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    ev = events[0]
    assert ev["web_searches"] == [{"query": "python typing", "result_count": 5, "error": None}]
    assert ev["web_citations"] == [{"url": "https://docs.python.org", "title": "PEP 484", "cited_text": "PEP 484"}]


async def test_agent_response_logs_web_fetches(tmp_path):
    activity = WebActivity(
        fetches=[WebFetchCall(url="https://example.com/doc", retrieved_at="2026-01-01T00:00:00Z")],
    )
    response = AgentResponse(
        stop_reason=StopReason.END_TURN,
        text="here",
        tool_calls=[],
        usage=TokenUsage(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            web_fetch_requests=1,
        ),
        web_activity=activity,
    )
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_agent_response(PHASE, response, 1)

    ev = read_events(tmp_path / "phase" / "p1.jsonl")[0]
    assert ev["web_fetches"] == [
        {"url": "https://example.com/doc", "retrieved_at": "2026-01-01T00:00:00Z", "error": None}
    ]
    assert ev["tokens"]["web_fetch_requests"] == 1


async def test_agent_response_logs_empty_web_activity(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    await cb.fire_agent_response(PHASE, make_response("hi"), 1)

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    assert events[0]["web_searches"] == []
    assert events[0]["web_fetches"] == []
    assert events[0]["web_citations"] == []


async def test_non_serializable_values_fall_back_to_str(tmp_path):
    logger = AgentLogger(tmp_path)
    cb = logger.as_callback_set()

    class Weird:
        def __repr__(self) -> str:
            return "WEIRD"

    tool_call = ToolCall(id="t1", name="x", input={"obj": Weird()})
    await cb.fire_tool_call(PHASE, tool_call, ToolResult(success=True, data="ok"), 1)

    events = read_events(tmp_path / "phase" / "p1.jsonl")
    assert "WEIRD" in events[0]["input"]["obj"]
