# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import UTC, datetime

from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.config.models import PhaseConfig
from ddev.ai.phases.base import FlowContext, Phase, PhaseOutcome
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.runtime.checkpoints import (
    CheckpointManager,
    CheckpointTokenInfo,
    FailedCheckpoint,
    GoalValidationRecord,
    SuccessCheckpoint,
)
from ddev.event_bus.exceptions import HookName, MessageProcessingError, ProcessorHookError


class _StubPhase(Phase):
    """Concrete Phase for lifecycle tests; execute() returns a deterministic PhaseOutcome."""

    def __init__(self, *args, outcome: PhaseOutcome | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._outcome = outcome or PhaseOutcome(memory_text="stub-memory")

    async def execute(self, context):
        return self._outcome


def _make_stub_phase(
    flow_dir,
    flow_context,
    message_queue,
    *,
    phase_id="p1",
    dependencies=None,
    outcome=None,
):
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    phase = _StubPhase(
        phase_id=phase_id,
        dependencies=dependencies or [],
        config=PhaseConfig(name=phase_id),
        checkpoint_manager=checkpoint_manager,
        context=flow_context,
        outcome=outcome,
    )
    phase.queue = message_queue
    return phase, checkpoint_manager


# ---------------------------------------------------------------------------
# Phase.build
# ---------------------------------------------------------------------------


def test_build_creates_properly_initialized_instance(flow_dir):
    checkpoint_manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    context = FlowContext(
        runtime_variables={"var1": "val1"},
        flow_variables={"var2": "val2"},
    )
    config = PhaseConfig(name="p1")

    phase = _StubPhase.build(
        phase_id="p1",
        config=config,
        deps=["dep1", "dep2"],
        resources=object(),
        checkpoint_manager=checkpoint_manager,
        context=context,
    )

    assert isinstance(phase, _StubPhase)
    assert phase._phase_id == "p1"
    assert phase._remaining_dependencies == {"dep1", "dep2"}
    assert phase._config is config
    assert phase._checkpoint_manager is checkpoint_manager
    assert phase._runtime_variables == {"var1": "val1"}
    assert phase._flow_variables == {"var2": "val2"}
    assert phase._callbacks is context.callbacks
    assert phase._logger is context.logger
    assert phase._executed is False


# ---------------------------------------------------------------------------
# Phase.on_success
# ---------------------------------------------------------------------------


async def test_on_success_emits_finished_message(flow_dir, flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_dir, flow_context, message_queue)

    await phase.on_success(PhaseTrigger(id="start", phase_id=None))

    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseTrigger)
    assert msg.phase_id == "p1"
    assert msg.id == "p1_finished"


# ---------------------------------------------------------------------------
# Phase.on_error
# ---------------------------------------------------------------------------


async def test_on_error_writes_failed_checkpoint(flow_dir, flow_context, message_queue):
    phase, mgr = _make_stub_phase(flow_dir, flow_context, message_queue)

    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["p1"]
    assert isinstance(checkpoint, FailedCheckpoint)
    assert checkpoint.error == "boom"
    assert checkpoint.started_at is None  # not started yet


async def test_on_error_emits_failed_message(flow_dir, flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_dir, flow_context, message_queue)

    wrapped = ProcessorHookError(
        HookName.ON_SUCCESS, "p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom")
    )
    await phase.on_error(wrapped)

    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseFailedMessage)
    assert msg.phase_id == "p1"
    assert msg.error == "boom"


async def test_on_error_writes_failed_checkpoint_after_start(flow_dir, flow_context, message_queue):
    phase, mgr = _make_stub_phase(flow_dir, flow_context, message_queue)
    phase._started_at = datetime.now(UTC)

    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["p1"]
    assert isinstance(checkpoint, FailedCheckpoint)
    assert checkpoint.started_at is not None


async def test_on_error_fires_phase_error_callback(flow_dir, message_queue):
    callback_set = CallbackSet()
    received: list[tuple[str, BaseException]] = []

    @callback_set.on_phase_error
    async def handler(phase_id: str, error: BaseException) -> None:
        received.append((phase_id, error))

    context = FlowContext(
        runtime_variables={},
        flow_variables={},
        callbacks=Callbacks([callback_set]),
    )
    phase, _ = _make_stub_phase(flow_dir, context, message_queue)
    original_error = RuntimeError("boom")
    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), original_error)

    await phase.on_error(wrapped)

    assert received == [("p1", original_error)]


# ---------------------------------------------------------------------------
# Phase.should_process_message
# ---------------------------------------------------------------------------


def test_should_process_returns_true_for_initial_trigger_on_root_phase(flow_dir, flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_dir, flow_context, message_queue)

    result = phase.should_process_message(PhaseTrigger(id="start", phase_id=None))

    assert result is True
    assert phase._executed is True


def test_should_process_returns_false_for_initial_trigger_on_dependent_phase(flow_dir, flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_dir, flow_context, message_queue, dependencies=["dep1"])

    result = phase.should_process_message(PhaseTrigger(id="start", phase_id=None))

    assert result is False
    assert phase._executed is False


def test_should_process_returns_false_for_unrelated_dep(flow_dir, flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_dir, flow_context, message_queue, dependencies=["dep1"])

    result = phase.should_process_message(PhaseTrigger(id="msg1", phase_id="other"))

    assert result is False
    assert phase._executed is False


def test_should_process_returns_false_while_deps_pending(flow_dir, flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_dir, flow_context, message_queue, dependencies=["dep1", "dep2"])

    result = phase.should_process_message(PhaseTrigger(id="msg1", phase_id="dep1"))

    assert result is False
    assert phase._remaining_dependencies == {"dep2"}
    assert phase._executed is False


def test_should_process_returns_true_when_last_dep_arrives(flow_dir, flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_dir, flow_context, message_queue, dependencies=["dep1", "dep2"])

    phase.should_process_message(PhaseTrigger(id="msg1", phase_id="dep1"))
    result = phase.should_process_message(PhaseTrigger(id="msg2", phase_id="dep2"))

    assert result is True
    assert phase._executed is True


def test_should_process_returns_false_after_already_executed(flow_dir, flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_dir, flow_context, message_queue)

    phase.should_process_message(PhaseTrigger(id="start", phase_id=None))
    result = phase.should_process_message(PhaseTrigger(id="start2", phase_id=None))

    assert result is False


# ---------------------------------------------------------------------------
# Phase lifecycle — memory path
# ---------------------------------------------------------------------------


async def test_process_message_writes_memory_and_checkpoint(flow_dir, flow_context, message_queue):
    """End-to-end Phase contract: memory_text is persisted, phase_data is recorded,
    token totals land in the checkpoint, and the success metadata is recorded.
    """
    outcome = PhaseOutcome(
        memory_text="stub-memory-body",
        total_input_tokens=123,
        total_output_tokens=45,
        goal_validations=[GoalValidationRecord(task="t1", attempts=1, final_valid=True)],
        checkpoint_data={"custom_field": "custom_value", "count": 7},
    )
    phase, mgr = _make_stub_phase(flow_dir, flow_context, message_queue, outcome=outcome)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.memory_content("p1") == "stub-memory-body"

    checkpoint = mgr.read()["p1"]
    assert isinstance(checkpoint, SuccessCheckpoint)
    assert checkpoint.tokens == CheckpointTokenInfo(total_input=123, total_output=45)
    assert checkpoint.memory_path == str(mgr.memory_path("p1"))
    assert checkpoint.phase_data == {"custom_field": "custom_value", "count": 7}
    assert checkpoint.goal_validations == [GoalValidationRecord(task="t1", attempts=1, final_valid=True)]
    assert checkpoint.started_at
    assert checkpoint.finished_at
