# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import UTC, datetime
from unittest.mock import MagicMock

from ddev.ai.phases.base import Phase, PhaseOutcome, _make_memory_resolver
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import PhaseConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
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
        config=PhaseConfig(),
        checkpoint_manager=checkpoint_manager,
        runtime_variables={},
        flow_variables={},
        config_dir=flow_dir,
        file_registry=FileRegistry(policy=FileAccessPolicy(write_root=flow_dir)),
        outcome=outcome,
    )
    phase.queue = message_queue
    return phase, checkpoint_manager


# ---------------------------------------------------------------------------
# _make_memory_resolver
# ---------------------------------------------------------------------------


def test_resolver_memory_suffix(tmp_path):
    mgr = CheckpointManager(tmp_path / "checkpoints.yaml")
    mgr.write_phase_checkpoint("x", {})
    mgr.write_memory("draft", "Draft memory content.")
    resolver = _make_memory_resolver(mgr)
    assert resolver("draft_memory") == "Draft memory content."


def test_resolver_non_memory_key():
    mgr = MagicMock()
    resolver = _make_memory_resolver(mgr)
    assert resolver("some_variable") == "<VARIABLE UNDEFINED: some_variable>"
    mgr.memory_content.assert_not_called()


def test_resolver_absent_memory(tmp_path):
    mgr = CheckpointManager(tmp_path / "checkpoints.yaml")
    resolver = _make_memory_resolver(mgr)
    assert resolver("nonexistent_memory") == "<MEMORY NOT FOUND: nonexistent>"


# ---------------------------------------------------------------------------
# Phase.on_success
# ---------------------------------------------------------------------------


async def test_on_success_emits_finished_message(flow_dir, message_queue):
    phase, _ = _make_stub_phase(flow_dir, message_queue)

    await phase.on_success(PhaseTrigger(id="start", phase_id=None))

    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseTrigger)
    assert msg.phase_id == "p1"
    assert msg.id == "p1_finished"


# ---------------------------------------------------------------------------
# Phase.on_error
# ---------------------------------------------------------------------------


async def test_on_error_writes_failed_checkpoint(flow_dir, message_queue):
    phase, mgr = _make_stub_phase(flow_dir, message_queue)

    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "failed"
    assert checkpoint["error"] == "boom"
    assert checkpoint["started_at"] is None  # not started yet


async def test_on_error_emits_failed_message(flow_dir, message_queue):
    phase, _ = _make_stub_phase(flow_dir, message_queue)

    wrapped = ProcessorHookError(
        HookName.ON_SUCCESS, "p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom")
    )
    await phase.on_error(wrapped)

    msg = message_queue.get_nowait()
    assert isinstance(msg, PhaseFailedMessage)
    assert msg.phase_id == "p1"
    assert msg.error == "boom"


async def test_on_error_writes_failed_checkpoint_after_start(flow_dir, message_queue):
    phase, mgr = _make_stub_phase(flow_dir, message_queue)
    phase._started_at = datetime.now(UTC)

    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["p1"]
    assert checkpoint["status"] == "failed"
    assert checkpoint["started_at"] is not None


# ---------------------------------------------------------------------------
# Phase.should_process_message
# ---------------------------------------------------------------------------


def test_should_process_returns_true_for_initial_trigger_on_root_phase(flow_dir, message_queue):
    phase, _ = _make_stub_phase(flow_dir, message_queue)

    result = phase.should_process_message(PhaseTrigger(id="start", phase_id=None))

    assert result is True
    assert phase._executed is True


def test_should_process_returns_false_for_initial_trigger_on_dependent_phase(flow_dir, message_queue):
    phase, _ = _make_stub_phase(flow_dir, message_queue, dependencies=["dep1"])

    result = phase.should_process_message(PhaseTrigger(id="start", phase_id=None))

    assert result is False
    assert phase._executed is False


def test_should_process_returns_false_for_unrelated_dep(flow_dir, message_queue):
    phase, _ = _make_stub_phase(flow_dir, message_queue, dependencies=["dep1"])

    result = phase.should_process_message(PhaseTrigger(id="msg1", phase_id="other"))

    assert result is False
    assert phase._executed is False


def test_should_process_returns_false_while_deps_pending(flow_dir, message_queue):
    phase, _ = _make_stub_phase(flow_dir, message_queue, dependencies=["dep1", "dep2"])

    result = phase.should_process_message(PhaseTrigger(id="msg1", phase_id="dep1"))

    assert result is False
    assert phase._remaining_dependencies == {"dep2"}
    assert phase._executed is False


def test_should_process_returns_true_when_last_dep_arrives(flow_dir, message_queue):
    phase, _ = _make_stub_phase(flow_dir, message_queue, dependencies=["dep1", "dep2"])

    phase.should_process_message(PhaseTrigger(id="msg1", phase_id="dep1"))
    result = phase.should_process_message(PhaseTrigger(id="msg2", phase_id="dep2"))

    assert result is True
    assert phase._executed is True


def test_should_process_returns_false_after_already_executed(flow_dir, message_queue):
    phase, _ = _make_stub_phase(flow_dir, message_queue)

    phase.should_process_message(PhaseTrigger(id="start", phase_id=None))
    result = phase.should_process_message(PhaseTrigger(id="start2", phase_id=None))

    assert result is False


# ---------------------------------------------------------------------------
# Phase lifecycle — memory path
# ---------------------------------------------------------------------------


async def test_failed_phase_omits_memory_path(flow_dir, message_queue):
    phase, mgr = _make_stub_phase(flow_dir, message_queue)

    wrapped = MessageProcessingError("p1", PhaseTrigger(id="start", phase_id=None), RuntimeError("boom"))
    await phase.on_error(wrapped)

    checkpoint = mgr.read()["p1"]
    assert "memory_path" not in checkpoint
