# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from typing import cast

import pytest

from ddev.ai.agent.build import AgentRuntime
from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.config.models import AgentConfig, TaskConfig
from ddev.ai.phases.goal import (
    GOAL_REVIEWER_RESET_THRESHOLD_PCT,
    GOAL_REVIEWER_SYSTEM_PROMPT,
    DeterministicCheck,
    ReviewerCheckResult,
    ReviewerParseError,
    ValidationAttemptsExhausted,
    _select_reviewer_message,
    build_reviewer_user_message,
    parse_reviewer_verdict,
    run_deterministic_checks,
    run_validation_loop,
)
from ddev.ai.phases.messages import TaskValidationStatus
from ddev.ai.react.process import ReActProcess
from ddev.ai.react.types import ReActResult
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.tools.registry import ToolRegistry
from tests.ai.config.utils import make_agent_config

from .helpers import MockAgent, make_goal_verdict, make_response

# ---------------------------------------------------------------------------
# parse_reviewer_verdict
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        (make_goal_verdict(True), (True, "")),
        (
            make_goal_verdict(
                False,
                "missing metric x",
                [{"id": "missing-x", "criterion": "metrics", "reason": "missing metric x"}],
            ),
            (False, "missing metric x"),
        ),
        (f"  {make_goal_verdict(True, 'ok')}  ", (True, "ok")),
        (
            make_goal_verdict(
                False,
                "missing x",
                [{"id": "x", "criterion": "files", "reason": "missing x"}],
            ),
            (False, "missing x"),
        ),
        (f"```json\n{make_goal_verdict(True)}\n```", (True, "")),
        (
            f"```\n{make_goal_verdict(False, 'no')}\n```",
            (False, "no"),
        ),
        (
            f"I read every file and verified the prefix.\nEverything checks out.\n{make_goal_verdict(True)}",
            (True, ""),
        ),
        (
            f"Detailed reasoning across\nseveral lines of prose.\n{make_goal_verdict(False, 'missing metric x')}\n",
            (False, "missing metric x"),
        ),
        ('{\n  "valid": true,\n  "reason": "ok",\n  "findings": []\n}', (True, "ok")),
    ],
    ids=[
        "plain_true",
        "plain_false",
        "whitespace",
        "structured_state",
        "fenced_json",
        "fenced_plain",
        "prose_then_verdict_line",
        "multiline_prose_then_verdict_line",
        "pretty_printed_pure_json",
    ],
)
def test_parse_reviewer_verdict_accepts(text, expected):
    verdict = parse_reviewer_verdict(text)
    assert verdict is not None
    assert (verdict["valid"], verdict["reason"]) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not json at all",
        '{"valid": "yes", "reason": "x"}',
        '{"valid": true, "reason": 42}',
        '{"reason": "x"}',
        '["valid", true]',
        '{"valid": false, "reason": "x", "findings": ["not structured"]}',
        '{"valid": true, "reason": ""}',
        '{"valid": false, "reason": "x", "findings": []}',
        '{"valid": true, "reason": "", "findings": [{"id": "x", "criterion": "x", "reason": "x"}]}',
    ],
    ids=[
        "empty",
        "prose",
        "valid_not_bool",
        "reason_not_str",
        "missing_valid",
        "not_object",
        "malformed_findings",
        "missing_findings",
        "rejection_without_findings",
        "valid_with_findings",
    ],
)
def test_parse_reviewer_verdict_rejects(text):
    assert parse_reviewer_verdict(text) is None


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


@pytest.mark.parametrize(
    "has_previous_check,context_pct,expected_reset,expected_section",
    [
        (False, None, False, "## Worker summary\nSUMMARY"),
        (True, None, False, "## Worker repair summary\nSUMMARY"),
        (True, GOAL_REVIEWER_RESET_THRESHOLD_PCT - 1, False, "## Worker repair summary\nSUMMARY"),
        (True, GOAL_REVIEWER_RESET_THRESHOLD_PCT, True, "## Previous reviewer verdict"),
        (True, GOAL_REVIEWER_RESET_THRESHOLD_PCT + 1, True, "## Previous reviewer verdict"),
    ],
    ids=["initial", "unknown", "below_threshold", "at_threshold", "above_threshold"],
)
def test_select_reviewer_message(
    has_previous_check: bool,
    context_pct: float | None,
    expected_reset: bool,
    expected_section: str,
) -> None:
    previous_check = None
    if has_previous_check:
        previous_check = ReviewerCheckResult(
            valid=False,
            reason="missing X",
            input_tokens=20,
            output_tokens=10,
            verdict_json=make_goal_verdict(False, "missing X"),
            context_pct=context_pct,
        )

    message, needs_reset = _select_reviewer_message(
        previous_check=previous_check,
        rendered_task_prompt="TASK",
        goal_text="GOAL",
        worker_summary="SUMMARY",
    )

    assert needs_reset is expected_reset
    assert expected_section in message
    if expected_reset:
        assert "## Original task\nTASK" in message
        assert "## Goal to verify\nGOAL" in message


# ---------------------------------------------------------------------------
# Helpers used by run_validation_loop tests
# ---------------------------------------------------------------------------


def _make_worker_process(responses):
    """ReActProcess wired to a MockAgent — used as the worker."""
    agent = MockAgent(list(responses))
    scope = AgentScope(owner_id="worker", role=AgentRole.PHASE, phase_id="worker")
    return ReActProcess(AgentRuntime(agent=agent, tool_registry=ToolRegistry([])), scope=scope), agent


class ReviewerProcessFactory:
    """Process factory returning a fixed reviewer agent wrapped in a ReActProcess."""

    def __init__(self, responses, callbacks: Callbacks | None = None) -> None:
        self.agent = MockAgent(list(responses))
        self.calls: list[dict[str, object]] = []
        self._callbacks = callbacks or Callbacks()

    def create(self, *, scope, agent_config: AgentConfig, system_prompt: str) -> ReActProcess:
        self.calls.append(
            {
                "agent_config": agent_config,
                "system_prompt": system_prompt,
                "owner_id": scope.owner_id,
                "phase_id": scope.phase_id,
            }
        )
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
# run_validation_loop
# ---------------------------------------------------------------------------


async def test_run_validation_loop_passes_on_first_attempt(tmp_path):
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
        [make_response(make_goal_verdict(True), 20, 10)],
        callbacks=Callbacks([run_logger.as_callback_set()]),
    )

    outcome = await run_validation_loop(
        task=TaskConfig(name="t1", prompt="x", goal="verify"),
        goal_text="verify",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=make_agent_config(tools=[]),
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
    assert builder_calls[0]["phase_id"] == "p1"

    log_path = tmp_path / "goal_reviewer" / "p1.goal.t1.jsonl"
    assert log_path.exists()
    events = {json.loads(line)["event"] for line in log_path.read_text().splitlines() if line.strip()}
    assert {"start", "finish"} <= events


async def test_run_validation_loop_inherits_parent_config_with_read_only_tools(tmp_path):
    worker_process, _ = _make_worker_process([])
    initial_result = ReActResult(
        final_response=make_response("did things"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    factory, builder_calls, _ = _reviewer_factory([make_response(make_goal_verdict(True), 20, 10)])
    parent_config = make_agent_config(
        provider="anthropic",
        tools=["read_file", "edit_file", "grep", "create_file"],
        model="custom-model",
        max_tokens=999,
    )

    await run_validation_loop(
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

    reviewer_config = cast(AgentConfig, builder_calls[0]["agent_config"])
    assert reviewer_config.provider == parent_config.provider
    assert reviewer_config.model == parent_config.model
    assert reviewer_config.max_tokens == parent_config.max_tokens
    assert reviewer_config.tools == ["read_file", "grep"]
    assert builder_calls[0]["system_prompt"] == GOAL_REVIEWER_SYSTEM_PROMPT
    assert builder_calls[0]["owner_id"] == "p1.goal.t1"


async def test_run_validation_loop_one_retry_then_pass(tmp_path):
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
            make_response(
                make_goal_verdict(False, "missing X"), 20, 10, context_pct=GOAL_REVIEWER_RESET_THRESHOLD_PCT - 1
            ),
            make_response(make_goal_verdict(True), 25, 12),
        ]
    )

    outcome = await run_validation_loop(
        task=TaskConfig(name="t1", prompt="x", goal="g"),
        goal_text="g",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=make_agent_config(tools=[]),
        process_factory=factory,
        callbacks=Callbacks(),
        phase_id="p1",
        compact_if_needed=_noop_compact,
    )

    assert outcome.attempts == 2
    assert outcome.final_result.final_response.text == "fixed it"
    assert len(worker_agent.send_calls) == 1
    worker_retry_message = worker_agent.send_calls[0]
    assert "missing X" in worker_retry_message
    assert '"valid": false' in worker_retry_message
    assert "g" in worker_retry_message
    assert "Reviewer verdict:" in worker_retry_message
    assert len(reviewer_agent.send_calls) == 2
    assert reviewer_agent.reset_call_count == 0
    assert "## Re-review instructions" not in reviewer_agent.send_calls[0]
    assert "## Re-review instructions" in reviewer_agent.send_calls[1]
    assert "## Previous reviewer verdict" not in reviewer_agent.send_calls[1]
    assert outcome.total_input_tokens == 20 + 25 + 30
    assert outcome.total_output_tokens == 10 + 12 + 15


async def test_run_validation_loop_resets_large_reviewer_context_before_retry(tmp_path):
    worker_process, _ = _make_worker_process([make_response("fixed it", 30, 15)])
    initial_result = ReActResult(
        final_response=make_response("initial work"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    previous_verdict = make_goal_verdict(False, "missing X")
    factory, _, reviewer_agent = _reviewer_factory(
        [
            make_response(previous_verdict, 20, 10, context_pct=GOAL_REVIEWER_RESET_THRESHOLD_PCT),
            make_response(make_goal_verdict(True), 25, 12),
        ]
    )

    outcome = await run_validation_loop(
        task=TaskConfig(name="t1", prompt="x", goal="g"),
        goal_text="GOAL",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=make_agent_config(tools=[]),
        process_factory=factory,
        callbacks=Callbacks(),
        phase_id="p1",
        compact_if_needed=_noop_compact,
    )

    assert outcome.attempts == 2
    assert reviewer_agent.reset_call_count == 1
    assert reviewer_agent.compact_call_count == 0
    assert len(reviewer_agent.send_calls) == 2
    retry_message = reviewer_agent.send_calls[1]
    assert "## Re-review instructions" in retry_message
    assert "## Original task\nTASK" in retry_message
    assert "## Goal to verify\nGOAL" in retry_message
    assert "## Previous reviewer verdict" in retry_message
    assert '"reason": "missing X"' in retry_message
    assert "## Worker repair summary\nfixed it" in retry_message


async def test_run_validation_loop_repairs_deterministic_failure_before_calling_reviewer() -> None:
    worker_process, worker_agent = _make_worker_process([make_response("fixed it", 30, 15)])
    initial_result = ReActResult(
        final_response=make_response("initial work"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    factory, builder_calls, reviewer_agent = _reviewer_factory([make_response(make_goal_verdict(True), 20, 10)])
    calls: list[str] = []
    schema_failures = iter(["`required_field` is missing", None])
    coverage_failures = iter(["`resource` is missing from the manifest", None])

    def check_artifact_schema() -> str | None:
        calls.append("artifact schema")
        return next(schema_failures)

    def check_resource_coverage() -> str | None:
        calls.append("resource coverage")
        return next(coverage_failures)

    def check_configuration() -> None:
        calls.append("configuration")
        return None

    outcome = await run_validation_loop(
        task=TaskConfig(name="t1", prompt="x", goal="g"),
        goal_text="g",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=make_agent_config(tools=[]),
        process_factory=factory,
        callbacks=Callbacks(),
        phase_id="p1",
        compact_if_needed=_noop_compact,
        deterministic_checks=(
            DeterministicCheck(name="artifact schema", run=check_artifact_schema),
            DeterministicCheck(name="resource coverage", run=check_resource_coverage),
            DeterministicCheck(name="configuration", run=check_configuration),
        ),
    )

    assert outcome.attempts == 2
    assert outcome.final_result.final_response.text == "fixed it"
    assert len(worker_agent.send_calls) == 1
    assert "Deterministic checks failed" in worker_agent.send_calls[0]
    assert "## artifact schema" in worker_agent.send_calls[0]
    assert "`required_field` is missing" in worker_agent.send_calls[0]
    assert "## resource coverage" in worker_agent.send_calls[0]
    assert "`resource` is missing from the manifest" in worker_agent.send_calls[0]
    assert "## configuration" not in worker_agent.send_calls[0]
    assert len(reviewer_agent.send_calls) == 1
    assert len(builder_calls) == 1
    assert calls == [
        "artifact schema",
        "resource coverage",
        "configuration",
        "artifact schema",
        "resource coverage",
        "configuration",
    ]
    assert outcome.total_input_tokens == 30 + 20
    assert outcome.total_output_tokens == 15 + 10


async def test_run_validation_loop_deterministic_exhaustion_never_creates_reviewer() -> None:
    worker_process, worker_agent = _make_worker_process([])
    initial_result = ReActResult(
        final_response=make_response("initial work"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    factory, builder_calls, reviewer_agent = _reviewer_factory([])
    events: list[tuple[str, TaskValidationStatus | None]] = []
    callback_set = CallbackSet()

    @callback_set.on_before_task_validation
    async def _before(_phase_id: str, _task_name: str, _attempt: int) -> None:
        events.append(("before", None))

    @callback_set.on_after_task_validation
    async def _after(
        _phase_id: str,
        _task_name: str,
        _attempt: int,
        status: TaskValidationStatus,
        _reason: str,
    ) -> None:
        events.append(("after", status))

    with pytest.raises(ValidationAttemptsExhausted, match=r"(?s)Last validation reason.*required_field") as exc_info:
        await run_validation_loop(
            task=TaskConfig(name="t1", prompt="x", goal="g", max_validation_attempts=1),
            goal_text="g",
            rendered_task_prompt="TASK",
            worker_process=worker_process,
            initial_result=initial_result,
            parent_agent_config=make_agent_config(tools=[]),
            process_factory=factory,
            callbacks=Callbacks([callback_set]),
            phase_id="p1",
            compact_if_needed=_noop_compact,
            deterministic_checks=(
                DeterministicCheck(name="artifact schema", run=lambda: "`required_field` is missing"),
            ),
        )

    assert exc_info.value.attempts == 1
    assert worker_agent.send_calls == []
    assert reviewer_agent.send_calls == []
    assert builder_calls == []
    assert events == [("before", None), ("after", TaskValidationStatus.FAILED)]


async def test_run_validation_loop_accepts_passing_deterministic_checks_without_goal() -> None:
    worker_process, worker_agent = _make_worker_process([])
    initial_result = ReActResult(
        final_response=make_response("initial work"),
        iterations=1,
        total_input_tokens=100,
        total_output_tokens=50,
        context_usage=None,
    )
    factory, builder_calls, reviewer_agent = _reviewer_factory([])
    statuses: list[TaskValidationStatus] = []
    callback_set = CallbackSet()

    @callback_set.on_after_task_validation
    async def _after(
        _phase_id: str,
        _task_name: str,
        _attempt: int,
        status: TaskValidationStatus,
        _reason: str,
    ) -> None:
        statuses.append(status)

    outcome = await run_validation_loop(
        task=TaskConfig(name="t1", prompt="x"),
        goal_text=None,
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=make_agent_config(tools=[]),
        process_factory=factory,
        callbacks=Callbacks([callback_set]),
        phase_id="p1",
        compact_if_needed=_noop_compact,
        deterministic_checks=(DeterministicCheck(name="artifact schema", run=lambda: None),),
    )

    assert outcome.attempts == 1
    assert outcome.final_result is initial_result
    assert worker_agent.send_calls == []
    assert reviewer_agent.send_calls == []
    assert builder_calls == []
    assert statuses == [TaskValidationStatus.PASSED]


def test_run_deterministic_checks_rejects_duplicate_names_before_running_checks() -> None:
    calls: list[str] = []
    checks = (
        DeterministicCheck(name="duplicate", run=lambda: calls.append("first")),
        DeterministicCheck(name="duplicate", run=lambda: calls.append("second")),
    )

    with pytest.raises(ValueError, match="must be unique.*duplicate"):
        run_deterministic_checks(checks)

    assert calls == []


@pytest.mark.parametrize(
    "checks,match",
    [
        pytest.param(
            (DeterministicCheck(name="  ", run=lambda: None),),
            "must not be blank",
            id="blank_name",
        ),
        pytest.param(
            (DeterministicCheck(name="incomplete", run=lambda: ""),),
            "blank failure reason",
            id="blank_failure_reason",
        ),
    ],
)
def test_run_deterministic_checks_rejects_invalid_checks(
    checks: tuple[DeterministicCheck, ...],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        run_deterministic_checks(checks)


def test_run_deterministic_checks_propagates_checker_exceptions() -> None:
    def broken_check() -> None:
        raise RuntimeError("catalog is unreadable")

    with pytest.raises(RuntimeError, match="catalog is unreadable"):
        run_deterministic_checks((DeterministicCheck(name="broken", run=broken_check),))


async def test_run_validation_loop_exhausts_attempts(tmp_path):
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
            make_response(make_goal_verdict(False, "first miss"), 5, 3),
            make_response(make_goal_verdict(False, "second miss"), 7, 4),
        ]
    )

    with pytest.raises(ValidationAttemptsExhausted, match="2 attempts") as exc_info:
        await run_validation_loop(
            task=TaskConfig(name="t1", prompt="x", goal="g", max_validation_attempts=2),
            goal_text="g",
            rendered_task_prompt="TASK",
            worker_process=worker_process,
            initial_result=initial_result,
            parent_agent_config=make_agent_config(tools=[]),
            process_factory=factory,
            callbacks=Callbacks(),
            phase_id="p1",
            compact_if_needed=_noop_compact,
        )

    err = exc_info.value
    assert err.input_tokens == 5 + 10 + 7
    assert err.output_tokens == 3 + 5 + 4


async def test_run_validation_loop_parse_retry_succeeds(tmp_path):
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
            make_response(make_goal_verdict(True), 7, 7),
        ]
    )

    outcome = await run_validation_loop(
        task=TaskConfig(name="t1", prompt="x", goal="g"),
        goal_text="g",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=make_agent_config(tools=[]),
        process_factory=factory,
        callbacks=Callbacks(),
        phase_id="p1",
        compact_if_needed=_noop_compact,
    )
    assert outcome.attempts == 1
    assert len(reviewer_agent.send_calls) == 2
    assert outcome.total_input_tokens == 5 + 7
    assert outcome.total_output_tokens == 5 + 7


async def test_run_validation_loop_parse_retry_fails_raises(tmp_path):
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

    with pytest.raises(ReviewerParseError) as exc_info:
        await run_validation_loop(
            task=TaskConfig(name="t1", prompt="x", goal="g"),
            goal_text="g",
            rendered_task_prompt="TASK",
            worker_process=worker_process,
            initial_result=initial_result,
            parent_agent_config=make_agent_config(tools=[]),
            process_factory=factory,
            callbacks=Callbacks(),
            phase_id="p1",
            compact_if_needed=_noop_compact,
        )

    err = exc_info.value
    assert err.input_tokens == 5 + 7
    assert err.output_tokens == 3 + 4


async def test_run_validation_loop_fires_callbacks(tmp_path):
    events: list = []
    cb_set = CallbackSet()

    @cb_set.on_before_task_validation
    async def _before(phase_id: str, task_name: str, attempt: int) -> None:
        events.append(("before", phase_id, task_name, attempt))

    @cb_set.on_after_task_validation
    async def _after(
        phase_id: str,
        task_name: str,
        attempt: int,
        status: TaskValidationStatus,
        reason: str,
    ) -> None:
        events.append(("after", phase_id, task_name, attempt, status, reason))

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
            make_response(make_goal_verdict(False, "fix X"), 0, 0),
            make_response(make_goal_verdict(True), 0, 0),
        ]
    )

    await run_validation_loop(
        task=TaskConfig(name="t1", prompt="x", goal="g"),
        goal_text="g",
        rendered_task_prompt="TASK",
        worker_process=worker_process,
        initial_result=initial_result,
        parent_agent_config=make_agent_config(tools=[]),
        process_factory=factory,
        callbacks=Callbacks([cb_set]),
        phase_id="p1",
        compact_if_needed=_noop_compact,
    )
    assert events == [
        ("before", "p1", "t1", 1),
        ("after", "p1", "t1", 1, TaskValidationStatus.RETRYING, "fix X"),
        ("before", "p1", "t1", 2),
        ("after", "p1", "t1", 2, TaskValidationStatus.PASSED, ""),
    ]
