# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import pytest

from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.phases.config import AgentConfig, TaskConfig
from ddev.ai.phases.goal import (
    GOAL_REVIEWER_SYSTEM_PROMPT,
    GoalAttemptsExhausted,
    GoalParseError,
    build_reviewer_user_message,
    parse_reviewer_output,
    render_goal_text,
    run_goal_loop,
)
from ddev.ai.react.process import ReActProcess
from ddev.ai.react.types import ReActResult
from ddev.ai.runtime.agent_log import AgentLogger
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


def test_render_goal_text_inline(tmp_path):
    result = render_goal_text(
        TaskConfig(name="t", prompt="x", goal="check ${name}"),
        None,
        {"name": "Alice"},
    )
    assert result == "check Alice"


def test_render_goal_text_from_ref():
    from unittest.mock import MagicMock

    resources = MagicMock()
    resources.goal.side_effect = lambda name: f"verify ${{{name}_target}}"
    result = render_goal_text(
        TaskConfig(name="t", prompt_ref="t", goal_ref="mygoal"),
        resources,
        {"mygoal_target": "endpoint"},
    )
    assert result == "verify endpoint"
    resources.goal.assert_called_once_with("mygoal")


def test_render_goal_text_forwards_resolver(tmp_path):
    result = render_goal_text(
        TaskConfig(name="t", prompt="x", goal="see ${draft_memory}"),
        None,
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
    scope = AgentScope(owner_id="worker", role=AgentRole.PHASE)
    return ReActProcess(AgentRuntime(agent=agent, tool_registry=ToolRegistry([])), scope=scope), agent


class ReviewerProcessFactory:
    """Process factory returning a fixed reviewer agent wrapped in a ReActProcess."""

    def __init__(self, responses, callbacks: Callbacks | None = None) -> None:
        self.agent = MockAgent(list(responses))
        self.calls: list[dict[str, object]] = []
        self._callbacks = callbacks or Callbacks()

    def create(self, *, scope, agent_config: AgentConfig, system_prompt: str) -> ReActProcess:
        self.calls.append({"agent_config": agent_config, "system_prompt": system_prompt, "owner_id": scope.owner_id})
        return ReActProcess(
            AgentRuntime(agent=self.agent, tool_registry=ToolRegistry([])),
            callbacks=self._callbacks,
            scope=scope,
        )


def _reviewer_factory(
    responses, callbacks: Callbacks | None = None
) -> tuple[ReviewerProcessFactory, list[dict[str, object]], MockAgent]:
    """Return a reviewer process factory plus its captured calls and agent."""
    factory = ReviewerProcessFactory(responses, callbacks)
    return factory, factory.calls, factory.agent


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
    run_logger = AgentLogger(tmp_path)
    factory, builder_calls, _ = _reviewer_factory(
        [make_response('{"valid": true, "reason": ""}', 20, 10)],
        callbacks=Callbacks([run_logger.as_callback_set()]),
    )

    outcome = await run_goal_loop(
        task=TaskConfig(name="t1", prompt="x", goal="verify"),
        goal_text="verify",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=AgentConfig(tools=[]),
        process_factory=factory,
        callbacks=Callbacks(),
        phase_id="p1",
        compact_if_needed=_noop_compact,
    )

    assert outcome.attempts == 1
    assert outcome.total_input_tokens == 20
    assert outcome.total_output_tokens == 10
    assert outcome.final_result is initial_result
    assert worker_agent.send_calls == []
    assert builder_calls[0]["owner_id"] == "p1.goal.t1"
    assert builder_calls[0]["system_prompt"] == GOAL_REVIEWER_SYSTEM_PROMPT

    log_path = tmp_path / "goal_reviewer" / "p1.goal.t1.jsonl"
    assert log_path.exists()
    events = {json.loads(line)["event"] for line in log_path.read_text().splitlines() if line.strip()}
    assert {"start", "finish"} <= events


async def test_run_goal_loop_derives_reviewer_runtime_policy(tmp_path):
    worker_process, _ = _make_worker_process([])
    initial_result = ReActResult(
        final_response=make_response("did things"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    factory, builder_calls, _ = _reviewer_factory([make_response('{"valid": true, "reason": ""}', 20, 10)])
    parent_config = AgentConfig(
        provider="anthropic",
        tools=["read_file", "edit_file", "grep", "create_file"],
        model="custom-model",
        max_tokens=999,
    )

    await run_goal_loop(
        task=TaskConfig(name="t1", prompt="x", goal="verify"),
        goal_text="verify",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=parent_config,
        process_factory=factory,
        callbacks=Callbacks(),
        phase_id="p1",
        compact_if_needed=_noop_compact,
    )

    reviewer_config = builder_calls[0]["agent_config"]
    assert reviewer_config.provider == "anthropic"
    assert reviewer_config.tools == ["read_file", "grep"]
    assert reviewer_config.model is None
    assert reviewer_config.max_tokens is None
    assert builder_calls[0]["system_prompt"] == GOAL_REVIEWER_SYSTEM_PROMPT
    assert builder_calls[0]["owner_id"] == "p1.goal.t1"


async def test_run_goal_loop_one_retry_then_pass(tmp_path):
    worker_process, worker_agent = _make_worker_process([make_response("fixed it", 30, 15)])
    initial_result = ReActResult(
        final_response=make_response("initial work"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    factory, _, reviewer_agent = _reviewer_factory(
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
        parent_agent_config=AgentConfig(tools=[]),
        process_factory=factory,
        callbacks=Callbacks(),
        phase_id="p1",
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
    factory, _, _ = _reviewer_factory(
        [
            make_response('{"valid": false, "reason": "first miss"}', 5, 3),
            make_response('{"valid": false, "reason": "second miss"}', 7, 4),
        ]
    )

    with pytest.raises(GoalAttemptsExhausted, match="2 attempts") as exc_info:
        await run_goal_loop(
            task=TaskConfig(name="t1", prompt="x", goal="g", max_goal_attempts=2),
            goal_text="g",
            rendered_task_prompt="TASK",
            worker_process=worker_process,
            initial_result=initial_result,
            parent_agent_config=AgentConfig(tools=[]),
            process_factory=factory,
            callbacks=Callbacks(),
            phase_id="p1",
            compact_if_needed=_noop_compact,
        )

    err = exc_info.value
    assert err.input_tokens == 5 + 10 + 7
    assert err.output_tokens == 3 + 5 + 4


async def test_run_goal_loop_parse_retry_succeeds(tmp_path):
    worker_process, _ = _make_worker_process([])
    initial_result = ReActResult(
        final_response=make_response("done"),
        iterations=1,
        total_input_tokens=0,
        total_output_tokens=0,
        context_usage=None,
    )
    factory, _, reviewer_agent = _reviewer_factory(
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
        parent_agent_config=AgentConfig(tools=[]),
        process_factory=factory,
        callbacks=Callbacks(),
        phase_id="p1",
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
    factory, _, _ = _reviewer_factory(
        [
            make_response("not json", 5, 3),
            make_response("still not json", 7, 4),
        ]
    )

    with pytest.raises(GoalParseError) as exc_info:
        await run_goal_loop(
            task=TaskConfig(name="t1", prompt="x", goal="g"),
            goal_text="g",
            rendered_task_prompt="TASK",
            worker_process=worker_process,
            initial_result=initial_result,
            parent_agent_config=AgentConfig(tools=[]),
            process_factory=factory,
            callbacks=Callbacks(),
            phase_id="p1",
            compact_if_needed=_noop_compact,
        )

    err = exc_info.value
    assert err.input_tokens == 5 + 7
    assert err.output_tokens == 3 + 4


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
    factory, _, _ = _reviewer_factory(
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
        parent_agent_config=AgentConfig(tools=[]),
        process_factory=factory,
        callbacks=Callbacks([cb_set]),
        phase_id="p1",
        compact_if_needed=_noop_compact,
    )
    assert events == [
        ("before", "t1", 1),
        ("after", "t1", 1, False, "fix X"),
        ("before", "t1", 2),
        ("after", "t1", 2, True, ""),
    ]
