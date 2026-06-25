# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import UTC, datetime

import pytest

from ddev.ai.phases.base import FlowContext, Phase, PhaseOutcome
from ddev.ai.phases.config import PhaseConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.runtime.checkpoints import (
    CheckpointManager,
    CheckpointStatus,
    FailedCheckpoint,
    SuccessCheckpoint,
    TokenUsage,
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
    flow_context,
    message_queue,
    *,
    phase_id="p1",
    dependencies=None,
    outcome=None,
):
    checkpoint_manager = CheckpointManager(flow_context.config_dir / "checkpoints.yaml")
    phase = _StubPhase(
        phase_id=phase_id,
        dependencies=dependencies or [],
        config=PhaseConfig(),
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
        config_dir=flow_dir,
    )
    config = PhaseConfig()

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
    assert phase._config_dir == flow_dir
    assert phase._callbacks is context.callbacks
    assert phase._logger is context.logger
    assert phase._executed is False


# ---------------------------------------------------------------------------
# Phase.on_success
# ---------------------------------------------------------------------------


async def test_on_success_emits_finished_message(flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_context, message_queue)

    await phase.on_success(PhaseTrigger(id="start", phase_id=None))

    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseTrigger)
    assert msg.phase_id == "p1"
    assert msg.id == "p1_finished"


# ---------------------------------------------------------------------------
# Phase.on_error
# ---------------------------------------------------------------------------


async def test_on_error_writes_failed_checkpoint(flow_context, message_queue):
    phase, mgr = _make_stub_phase(flow_context, message_queue)

    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["p1"]
    assert isinstance(checkpoint, FailedCheckpoint)
    assert checkpoint.status == CheckpointStatus.FAILED
    assert checkpoint.error == "boom"
    assert checkpoint.started_at is None  # not started yet


async def test_on_error_emits_failed_message(flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_context, message_queue)

    wrapped = ProcessorHookError(
        HookName.ON_SUCCESS, "p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom")
    )
    await phase.on_error(wrapped)

    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseFailedMessage)
    assert msg.phase_id == "p1"
    assert msg.error == "boom"


async def test_on_error_writes_failed_checkpoint_after_start(flow_context, message_queue):
    phase, mgr = _make_stub_phase(flow_context, message_queue)
    phase._started_at = datetime.now(UTC)

    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["p1"]
    assert isinstance(checkpoint, FailedCheckpoint)
    assert checkpoint.status == CheckpointStatus.FAILED
    assert checkpoint.started_at is not None


# ---------------------------------------------------------------------------
# Phase.should_process_message
# ---------------------------------------------------------------------------


def test_should_process_returns_true_for_initial_trigger_on_root_phase(flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_context, message_queue)

    result = phase.should_process_message(PhaseTrigger(id="start", phase_id=None))

    assert result is True
    assert phase._executed is True


def test_should_process_returns_false_for_initial_trigger_on_dependent_phase(flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_context, message_queue, dependencies=["dep1"])

    result = phase.should_process_message(PhaseTrigger(id="start", phase_id=None))

    assert result is False
    assert phase._executed is False


def test_should_process_returns_false_for_unrelated_dep(flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_context, message_queue, dependencies=["dep1"])

    result = phase.should_process_message(PhaseTrigger(id="msg1", phase_id="other"))

    assert result is False
    assert phase._executed is False


def test_should_process_returns_false_while_deps_pending(flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_context, message_queue, dependencies=["dep1", "dep2"])

    result = phase.should_process_message(PhaseTrigger(id="msg1", phase_id="dep1"))

    assert result is False
    assert phase._remaining_dependencies == {"dep2"}
    assert phase._executed is False


def test_should_process_returns_true_when_last_dep_arrives(flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_context, message_queue, dependencies=["dep1", "dep2"])

    phase.should_process_message(PhaseTrigger(id="msg1", phase_id="dep1"))
    result = phase.should_process_message(PhaseTrigger(id="msg2", phase_id="dep2"))

    assert result is True
    assert phase._executed is True


def test_should_process_returns_false_after_already_executed(flow_context, message_queue):
    phase, _ = _make_stub_phase(flow_context, message_queue)

    phase.should_process_message(PhaseTrigger(id="start", phase_id=None))
    result = phase.should_process_message(PhaseTrigger(id="start2", phase_id=None))

    assert result is False


# ---------------------------------------------------------------------------
# Phase lifecycle — memory path
# ---------------------------------------------------------------------------


async def test_process_message_writes_memory_and_checkpoint(flow_context, message_queue):
    """End-to-end Phase contract: memory_text is persisted, extra_checkpoint merges,
    token totals land in the checkpoint, and the success metadata is recorded.
    """
    outcome = PhaseOutcome(
        memory_text="stub-memory-body",
        total_input_tokens=123,
        total_output_tokens=45,
        extra_checkpoint={"custom_field": "custom_value", "count": 7},
    )
    phase, mgr = _make_stub_phase(flow_context, message_queue, outcome=outcome)

    await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.memory_content("p1") == "stub-memory-body"

    checkpoint = mgr.read()["p1"]
    assert isinstance(checkpoint, SuccessCheckpoint)
    assert checkpoint.status == CheckpointStatus.SUCCESS
    assert checkpoint.tokens == TokenUsage(total_input=123, total_output=45)
    assert checkpoint.memory_path == str(mgr.memory_path("p1"))
    assert checkpoint.custom_field == "custom_value"
    assert checkpoint.count == 7
    assert checkpoint.started_at
    assert checkpoint.finished_at


@pytest.mark.parametrize(
    "reserved_key",
    ["status", "started_at", "finished_at", "tokens", "memory_path"],
)
async def test_extra_checkpoint_cannot_override_reserved_keys(flow_context, message_queue, reserved_key):
    outcome = PhaseOutcome(memory_text="m", extra_checkpoint={reserved_key: "evil"})
    phase, mgr = _make_stub_phase(flow_context, message_queue, outcome=outcome)

    with pytest.raises(ValueError, match=f"reserved keys.*{reserved_key}"):
        await phase.process_message(PhaseTrigger(id="start", phase_id=None))

    assert mgr.read() == {}
    assert not mgr.memory_path("p1").exists()


async def test_failed_phase_omits_memory_path(flow_context, message_queue):
    phase, mgr = _make_stub_phase(flow_context, message_queue)

    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["p1"]
    assert "memory_path" not in checkpoint
