# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import pytest

from ddev.ai.agent.types import AgentResponse, StopReason, TokenUsage, ToolCall
from ddev.ai.callbacks.file_logger import FileLogger
from ddev.ai.tools.core.types import ToolResult


def make_response(text: str = "", stop_reason: StopReason = StopReason.END_TURN) -> AgentResponse:
    return AgentResponse(
        stop_reason=stop_reason,
        text=text,
        tool_calls=[],
        usage=TokenUsage(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
    )


def read_events(log_path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# File mechanics
# ---------------------------------------------------------------------------


def test_log_entries_are_valid_jsonl_with_timestamp(tmp_path):
    log_path = tmp_path / "log.jsonl"
    logger = FileLogger(log_path)
    logger.log_start(system_prompt="sys", prompt="go", tools=["read_file"])
    logger.log_finish(success=True, iterations=1)
    logger.close()

    events = read_events(log_path)
    assert len(events) == 2
    assert all("ts" in e for e in events)
    assert events[0]["event"] == "start"
    assert events[1]["event"] == "finish"


def test_flush_after_each_write(tmp_path):
    log_path = tmp_path / "log.jsonl"
    logger = FileLogger(log_path)
    logger.log_start(system_prompt="s", prompt="p", tools=[])
    # A second file handle reads the line without closing the logger first
    assert log_path.read_text(encoding="utf-8").strip() != ""
    logger.close()


def test_close_is_idempotent_and_prevents_further_writes(tmp_path):
    log_path = tmp_path / "log.jsonl"
    logger = FileLogger(log_path)
    logger.log_start(system_prompt="s", prompt="p", tools=[])
    logger.close()
    logger.close()  # must not raise
    logger.log_finish(success=False)  # must not write
    assert len(read_events(log_path)) == 1


def test_constructor_requires_existing_parent(tmp_path):
    with pytest.raises(OSError):
        FileLogger(tmp_path / "doesnotexist" / "log.jsonl")


def test_non_serializable_values_use_str_repr(tmp_path):
    log_path = tmp_path / "log.jsonl"
    logger = FileLogger(log_path)

    class Unserializable:
        def __repr__(self):
            return "<Unserializable>"

    logger.log_finish(success=True, extra=Unserializable())
    logger.close()

    assert read_events(log_path)[0]["extra"] == "<Unserializable>"


# ---------------------------------------------------------------------------
# Callbacks wiring
# ---------------------------------------------------------------------------


async def test_build_callbacks_fires_all_event_types(tmp_path):
    log_path = tmp_path / "log.jsonl"
    logger = FileLogger(log_path)
    callbacks = logger.build_callbacks()

    tool_call = ToolCall(id="tc1", name="read_file", input={"path": "/f"})
    tool_result = ToolResult(success=True, data="content")

    await callbacks.fire_before_agent_send(2)
    await callbacks.fire_agent_response(make_response("hi"), 2)
    await callbacks.fire_tool_call(tool_call, tool_result, 2)
    await callbacks.fire_before_compact()
    await callbacks.fire_after_compact()
    await callbacks.fire_error(ValueError("oops"))
    logger.close()

    events = {e["event"]: e for e in read_events(log_path)}

    assert events["before_agent_send"]["iter"] == 2
    assert events["agent_response"]["text"] == "hi"
    assert events["agent_response"]["iter"] == 2
    assert events["tool_call"]["tool_call_id"] == "tc1"
    assert events["tool_call"]["result"]["success"] is True
    assert "before_compact" in events
    assert "after_compact" in events
    assert "ValueError" in events["error"]["exception"]
