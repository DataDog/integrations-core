# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import pytest

from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.phases.config import TaskConfig
from ddev.ai.phases.goal import (
    GoalAttemptsExhausted,
    GoalParseError,
    build_reviewer_user_message,
    parse_reviewer_output,
    render_goal_text,
    run_goal_loop,
)
from ddev.ai.react.process import ReActProcess
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.registry import ToolRegistry

from .conftest import MockAgent, make_response, resolve_key

# ---------------------------------------------------------------------------
# parse_reviewer_output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ('{"valid": true, "reason": ""}', (True, "")),
        ('{"valid": false, "reason": "missing metric x"}', (False, "missing metric x")),
        ('  {"valid": true, "reason": "ok"}  ', (True, "ok")),
        ('```json\n{"valid": true, "reason": ""}\n```', (True, "")),
        ('```\n{"valid": false, "reason": "no"}\n```', (False, "no")),
    ],
    ids=["plain_true", "plain_false", "whitespace", "fenced_json", "fenced_plain"],
)
def test_parse_reviewer_output_accepts(text, expected):
    assert parse_reviewer_output(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json at all",
        '{"valid": "yes", "reason": "x"}',
        '{"valid": true, "reason": 42}',
        '{"reason": "x"}',
        '["valid", true]',
    ],
    ids=["empty", "prose", "valid_not_bool", "reason_not_str", "missing_valid", "not_object"],
)
def test_parse_reviewer_output_rejects(text):
    assert parse_reviewer_output(text) is None


# ---------------------------------------------------------------------------
# render_goal_text
# ---------------------------------------------------------------------------


def test_render_goal_text_inline_and_path(tmp_path):
    inline = render_goal_text(
        TaskConfig(name="t", prompt="x", goal="check ${name}"),
        tmp_path,
        {"name": "Alice"},
        None,
    )
    assert inline == "check Alice"

    (tmp_path / "goal.md").write_text("verify ${target}")
    from_file = render_goal_text(
        TaskConfig(name="t", prompt="x", goal_path="goal.md"),
        tmp_path,
        {"target": "endpoint"},
        None,
    )
    assert from_file == "verify endpoint"


def test_render_goal_text_forwards_resolver(tmp_path):
    result = render_goal_text(
        TaskConfig(name="t", prompt="x", goal="see ${draft_memory}"),
        tmp_path,
        {},
        resolve_key,
    )
    assert result == "see resolved(draft_memory)"


# ---------------------------------------------------------------------------
# build_reviewer_user_message
# ---------------------------------------------------------------------------


def test_build_reviewer_user_message_sections():
    msg = build_reviewer_user_message(
        rendered_task_prompt="TASK",
        goal_text="GOAL",
        worker_summary="SUMMARY",
    )
    assert "## Original task\nTASK" in msg
    assert "## Goal to verify\nGOAL" in msg
    assert "## Worker summary\nSUMMARY" in msg


# ---------------------------------------------------------------------------
# Helpers used by run_goal_loop tests
# ---------------------------------------------------------------------------


def _make_worker_process(responses):
    """ReActProcess wired to a MockAgent — used as the worker."""
    agent = MockAgent(list(responses))
    return ReActProcess(agent=agent, tool_registry=ToolRegistry([])), agent


def _reviewer_builder(responses):
    """A GoalAgentBuilder that returns a fresh MockAgent + empty ToolRegistry."""
    agent = MockAgent(list(responses))
    calls: list[str] = []

    def builder(owner_id):
        calls.append(owner_id)
        return agent, ToolRegistry([])

    return builder, calls, agent


async def _noop_compact(_):
    return 0, 0


# ---------------------------------------------------------------------------
# run_goal_loop
# ---------------------------------------------------------------------------


async def test_run_goal_loop_passes_on_first_attempt(tmp_path):
    worker_process, worker_agent = _make_worker_process([])
    initial_result = ReActResult(
        final_response=make_response("did things"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    builder, builder_calls, _ = _reviewer_builder([make_response('{"valid": true, "reason": ""}', 20, 10)])

    outcome = await run_goal_loop(
        task=TaskConfig(name="t1", prompt="x", goal="verify"),
        goal_text="verify",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        goal_agent_builder=builder,
        callbacks=Callbacks(),
        phase_id="p1",
        log_root=tmp_path,
        compact_if_needed=_noop_compact,
    )

    assert outcome.attempts == 1
    assert outcome.total_input_tokens == 20
    assert outcome.total_output_tokens == 10
    assert outcome.final_result is initial_result
    assert worker_agent.send_calls == []
    assert builder_calls == ["p1.goal.t1"]

    log_path = tmp_path / "goal_agent" / "p1" / "t1.jsonl"
    assert log_path.exists()
    events = {json.loads(line)["event"] for line in log_path.read_text().splitlines() if line.strip()}
    assert {"start", "finish"} <= events


async def test_run_goal_loop_one_retry_then_pass(tmp_path):
    worker_process, worker_agent = _make_worker_process([make_response("fixed it", 30, 15)])
    initial_result = ReActResult(
        final_response=make_response("initial work"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    builder, _, reviewer_agent = _reviewer_builder(
        [
            make_response('{"valid": false, "reason": "missing X"}', 20, 10),
            make_response('{"valid": true, "reason": ""}', 25, 12),
        ]
    )

    outcome = await run_goal_loop(
        task=TaskConfig(name="t1", prompt="x", goal="g"),
        goal_text="g",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        goal_agent_builder=builder,
        callbacks=Callbacks(),
        phase_id="p1",
        log_root=tmp_path,
        compact_if_needed=_noop_compact,
    )

    assert outcome.attempts == 2
    assert outcome.final_result.final_response.text == "fixed it"
    assert len(worker_agent.send_calls) == 1
    assert "missing X" in worker_agent.send_calls[0]
    assert "g" in worker_agent.send_calls[0]
    assert len(reviewer_agent.send_calls) == 2
    assert outcome.total_input_tokens == 20 + 25 + 30
    assert outcome.total_output_tokens == 10 + 12 + 15


async def test_run_goal_loop_exhausts_attempts(tmp_path):
    worker_process, _ = _make_worker_process([make_response("attempt 2", 10, 5)])
    initial_result = ReActResult(
        final_response=make_response("attempt 1"),
        iterations=1,
        total_input_tokens=10,
        total_output_tokens=5,
        context_usage=None,
    )
    builder, _, _ = _reviewer_builder(
        [
            make_response('{"valid": false, "reason": "first miss"}', 5, 5),
            make_response('{"valid": false, "reason": "second miss"}', 5, 5),
        ]
    )

    with pytest.raises(GoalAttemptsExhausted, match="2 attempts"):
        await run_goal_loop(
            task=TaskConfig(name="t1", prompt="x", goal="g", max_goal_attempts=2),
            goal_text="g",
            rendered_task_prompt="TASK",
            worker_process=worker_process,
            initial_result=initial_result,
            goal_agent_builder=builder,
            callbacks=Callbacks(),
            phase_id="p1",
            log_root=tmp_path,
            compact_if_needed=_noop_compact,
        )


async def test_run_goal_loop_parse_retry_succeeds(tmp_path):
    worker_process, _ = _make_worker_process([])
    initial_result = ReActResult(
        final_response=make_response("done"),
        iterations=1,
        total_input_tokens=0,
        total_output_tokens=0,
        context_usage=None,
    )
    builder, _, reviewer_agent = _reviewer_builder(
        [
            make_response("not json", 5, 5),
            make_response('{"valid": true, "reason": ""}', 7, 7),
        ]
    )

    outcome = await run_goal_loop(
        task=TaskConfig(name="t1", prompt="x", goal="g"),
        goal_text="g",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        goal_agent_builder=builder,
        callbacks=Callbacks(),
        phase_id="p1",
        log_root=tmp_path,
        compact_if_needed=_noop_compact,
    )
    assert outcome.attempts == 1
    assert len(reviewer_agent.send_calls) == 2
    assert outcome.total_input_tokens == 5 + 7
    assert outcome.total_output_tokens == 5 + 7


async def test_run_goal_loop_parse_retry_fails_raises(tmp_path):
    worker_process, _ = _make_worker_process([])
    initial_result = ReActResult(
        final_response=make_response("done"),
        iterations=1,
        total_input_tokens=0,
        total_output_tokens=0,
        context_usage=None,
    )
    builder, _, _ = _reviewer_builder(
        [
            make_response("not json", 5, 5),
            make_response("still not json", 5, 5),
        ]
    )

    with pytest.raises(GoalParseError):
        await run_goal_loop(
            task=TaskConfig(name="t1", prompt="x", goal="g"),
            goal_text="g",
            rendered_task_prompt="TASK",
            worker_process=worker_process,
            initial_result=initial_result,
            goal_agent_builder=builder,
            callbacks=Callbacks(),
            phase_id="p1",
            log_root=tmp_path,
            compact_if_needed=_noop_compact,
        )


async def test_run_goal_loop_fires_callbacks(tmp_path):
    events: list = []
    cb_set = CallbackSet()

    @cb_set.on_before_goal_check
    async def _before(task_name, attempt):
        events.append(("before", task_name, attempt))

    @cb_set.on_after_goal_check
    async def _after(task_name, attempt, valid, reason):
        events.append(("after", task_name, attempt, valid, reason))

    worker_process, _ = _make_worker_process([make_response("attempt 2", 0, 0)])
    initial_result = ReActResult(
        final_response=make_response("attempt 1"),
        iterations=1,
        total_input_tokens=0,
        total_output_tokens=0,
        context_usage=None,
    )
    builder, _, _ = _reviewer_builder(
        [
            make_response('{"valid": false, "reason": "fix X"}', 0, 0),
            make_response('{"valid": true, "reason": ""}', 0, 0),
        ]
    )

    await run_goal_loop(
        task=TaskConfig(name="t1", prompt="x", goal="g"),
        goal_text="g",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        goal_agent_builder=builder,
        callbacks=Callbacks([cb_set]),
        phase_id="p1",
        log_root=tmp_path,
        compact_if_needed=_noop_compact,
    )
    assert events == [
        ("before", "t1", 1),
        ("after", "t1", 1, False, "fix X"),
        ("before", "t1", 2),
        ("after", "t1", 2, True, ""),
    ]
