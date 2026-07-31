# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from ddev.ai.agent.anthropic_provider import DEFAULT_MODEL
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.callbacks.callbacks import Callbacks, CallbackSet
from ddev.ai.config.engine import ConfigurationEngine
from ddev.ai.config.errors import ConfigError
from ddev.ai.constants import CORE_PHASES_DIR, CORE_PHASES_PACKAGE
from ddev.ai.phases.base import Phase, PhaseOutcome
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.registry import PhaseRegistry
from ddev.ai.runtime.checkpoints import CancelledCheckpoint, CheckpointManager, CheckpointStatus
from ddev.ai.runtime.orchestrator import PhaseOrchestrator
from ddev.ai.runtime.outcome import (
    FailureKind,
    PhaseReportStatus,
    RunOutcome,
    RunOutcomeBuildError,
    RunOutcomePersistenceError,
    RunOutcomeStore,
    RunSummaryMetadata,
    RunSummaryStatus,
    RunVerdict,
)
from ddev.ai.runtime.summary import RunSummaryAttempt
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError, HookName, OrchestratorHookError

from .helpers import make_checkpoint


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


@pytest.fixture
def file_access_policy(tmp_path) -> FileAccessPolicy:
    return FileAccessPolicy(write_root=tmp_path)


@pytest.fixture
def provider_registry() -> AgentProviderRegistry:
    registry = AgentProviderRegistry()
    provider = MagicMock()
    provider.default_model.return_value = DEFAULT_MODEL
    provider.supported_models.return_value = frozenset({DEFAULT_MODEL})
    registry.register("anthropic", provider)
    return registry


@pytest.fixture
def core_dir(tmp_path) -> Path:
    """A core config dir with a 'writer' agent and a two-phase 'demo' flow ('a' root, 'b' after 'a')."""
    core = tmp_path / "core"
    write(core / "agents" / "writer.md", "---\ntype: agent\nname: writer\nmodel: sonnet\n---\nsystem prompt")
    write(
        core / "demo.yaml",
        "- type: phase\n  config:\n    name: a\n    agent: writer\n"
        "    tasks:\n      - name: task_a\n        prompt: task a\n"
        "- type: phase\n  config:\n    name: b\n    agent: writer\n"
        "    tasks:\n      - name: task_b\n        prompt: task b\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: a\n      - phase: b\n        dependencies: [a]\n",
    )
    return core


@pytest.fixture
def make_orchestrator(file_access_policy, provider_registry, tmp_path):
    """Composition root: build a registry, discover core phases, build the engine, build the orchestrator.

    Pass ``core_dir`` to point the engine at a config fixture and ``flow_name`` to select the flow.
    Any constructor kwarg can be overridden. The built ``PhaseRegistry`` is returned alongside so
    tests can register extra phase classes before ``on_initialize``.
    """

    def _make(
        core_dir: Path | None = None,
        flow_name: str = "demo",
        register_phases: dict[str, type[Phase]] | None = None,
        **overrides: Any,
    ) -> tuple[PhaseOrchestrator, PhaseRegistry, ConfigurationEngine]:
        registry = PhaseRegistry()
        registry.register_from(CORE_PHASES_DIR, CORE_PHASES_PACKAGE)
        for name, cls in (register_phases or {}).items():
            registry.register(name, cls)
        engine = ConfigurationEngine(
            core_dir=core_dir if core_dir is not None else tmp_path,
            user_dirs=[],
            phase_registry=registry,
            provider_registry=provider_registry,
        )
        resolved = engine.get_flow(flow_name)
        kwargs: dict[str, Any] = {
            "resolved_flow": resolved,
            "phase_registry": registry,
            "checkpoint_path": tmp_path / "checkpoints.yaml",
            "runtime_variables": {},
            "provider_registry": provider_registry,
            "file_access_policy": file_access_policy,
            **overrides,
        }
        return PhaseOrchestrator(**kwargs), registry, engine

    return _make


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_message_received
# ---------------------------------------------------------------------------


async def test_on_message_received_fatal_on_phase_failed(core_dir, make_orchestrator):
    orchestrator, _, _ = make_orchestrator(core_dir)
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="something broke")

    with pytest.raises(FatalProcessingError, match="Phase 'p1' failed"):
        await orchestrator.on_message_received(msg)

    assert orchestrator.failed_phase == "p1"


async def test_on_message_received_ignores_other_messages(core_dir, make_orchestrator):
    orchestrator, _, _ = make_orchestrator(core_dir)
    await orchestrator.on_message_received(PhaseTrigger(id="start", phase_id=None))
    await orchestrator.on_message_received(PhaseTrigger(id="f1", phase_id="p1"))


async def test_on_message_received_fires_run_error_callback(core_dir, make_orchestrator):
    callback_set = CallbackSet()
    received: list[bool] = []

    @callback_set.on_run_error
    async def handler() -> None:
        received.append(True)

    orchestrator, _, _ = make_orchestrator(core_dir, callbacks=Callbacks([callback_set]))
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="something broke")

    with pytest.raises(FatalProcessingError):
        await orchestrator.on_message_received(msg)

    assert received == [True]


async def test_on_error_does_not_fire_phase_failure_callback(core_dir, make_orchestrator):
    callback_set = CallbackSet()
    received: list[bool] = []

    @callback_set.on_run_error
    async def handler() -> None:
        received.append(True)

    orchestrator, _, _ = make_orchestrator(core_dir, callbacks=Callbacks([callback_set]))
    original_error = RuntimeError("scheduler broke")
    wrapped = OrchestratorHookError(HookName.ON_INITIALIZE, original_error)

    with pytest.raises(FatalProcessingError):
        await orchestrator.on_error(wrapped)

    assert received == []


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize
# ---------------------------------------------------------------------------


def test_max_timeout_comes_from_runtime_variables(core_dir: Path, make_orchestrator: Any):
    orchestrator, _, _ = make_orchestrator(core_dir, runtime_variables={"max_timeout": "120"})

    assert orchestrator._max_timeout == 120


async def test_on_initialize_registers_all_flow_phases(core_dir, make_orchestrator):
    orchestrator, _, _ = make_orchestrator(core_dir)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    assert {p.name for p in processors} == {"a", "b"}


async def test_on_initialize_wires_dependencies(core_dir, make_orchestrator):
    orchestrator, _, _ = make_orchestrator(core_dir)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    phases_by_name = {p.name: p for p in processors}
    assert phases_by_name["a"]._remaining_dependencies == set()
    assert phases_by_name["b"]._remaining_dependencies == {"a"}


async def test_on_initialize_submits_initial_phase_trigger(core_dir, make_orchestrator):
    orchestrator, _, _ = make_orchestrator(core_dir)
    await orchestrator.on_initialize()

    assert not orchestrator._queue.empty()
    msg = orchestrator._queue.get_nowait()
    assert isinstance(msg, PhaseTrigger)
    assert msg.phase_id is None


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_finalize
# ---------------------------------------------------------------------------


async def test_on_finalize_no_failure_is_noop(core_dir, make_orchestrator):
    orchestrator, _, _ = make_orchestrator(core_dir)
    await orchestrator.on_finalize(None)  # must not raise


async def test_on_finalize_after_phase_failed_logs(core_dir, make_orchestrator, caplog):
    orchestrator, _, _ = make_orchestrator(core_dir)
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="boom")
    exc = FatalProcessingError("Phase 'p1' failed: boom")
    with pytest.raises(FatalProcessingError):
        await orchestrator.on_message_received(msg)

    with caplog.at_level(logging.ERROR):
        await orchestrator.on_finalize(exc)  # must not raise

    assert any("Pipeline aborted" in r.message and "p1" in r.message and "boom" in r.message for r in caplog.records)


async def test_on_finalize_no_exception_no_log(core_dir, make_orchestrator, caplog):
    orchestrator, _, _ = make_orchestrator(core_dir)
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="boom")
    with pytest.raises(FatalProcessingError):
        await orchestrator.on_message_received(msg)

    with caplog.at_level(logging.ERROR):
        await orchestrator.on_finalize(None)  # exception=None means clean exit — no log

    assert not any("Pipeline aborted" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# End-to-end run
# ---------------------------------------------------------------------------


def test_run_executes_phases_in_dependency_order(tmp_path, make_orchestrator):
    """Full pipeline success: 'a' then 'b' (b depends on a), both checkpointed, run() completes."""
    core = tmp_path / "ok_core"
    write(
        core / "f.yaml",
        "- type: phase\n  config:\n    name: a\n    class: RecordingPhase\n"
        "- type: phase\n  config:\n    name: b\n    class: RecordingPhase\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: a\n      - phase: b\n        dependencies: [a]\n",
    )

    executed: list[str] = []

    class RecordingPhase(Phase):
        async def execute(self, context):
            executed.append(self._phase_id)
            return PhaseOutcome(memory_text=f"{self._phase_id} done")

    checkpoint_path = tmp_path / "checkpoints.yaml"
    callback_set = CallbackSet()
    finished: list[RunOutcome] = []

    @callback_set.on_run_finished
    async def on_run_finished(outcome: RunOutcome) -> None:
        finished.append(outcome)

    orchestrator, _, _ = make_orchestrator(
        core,
        grace_period=0.1,
        register_phases={"RecordingPhase": RecordingPhase},
        checkpoint_path=checkpoint_path,
        callbacks=Callbacks([callback_set]),
    )

    orchestrator.run()  # must not raise

    assert executed == ["a", "b"]

    mgr = CheckpointManager(checkpoint_path)
    checkpoints = mgr.read()
    assert checkpoints["a"].status == CheckpointStatus.SUCCESS
    assert checkpoints["b"].status == CheckpointStatus.SUCCESS
    assert orchestrator.outcome is not None
    assert orchestrator.outcome.verdict is RunVerdict.SUCCEEDED
    assert RunOutcomeStore(tmp_path / "run.yaml").read() == orchestrator.outcome
    assert finished == [orchestrator.outcome]


def test_max_timeout_writes_cancelled_checkpoint_for_running_phase(tmp_path, make_orchestrator):
    core = tmp_path / "timeout_core"
    write(
        core / "f.yaml",
        "- type: phase\n  config:\n    name: waiting\n    class: WaitingPhase\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: waiting\n",
    )

    class WaitingPhase(Phase):
        async def execute(self, context):
            await asyncio.Event().wait()
            return PhaseOutcome(memory_text="unreachable")

    checkpoint_path = tmp_path / "timeout-checkpoints.yaml"
    orchestrator, _, _ = make_orchestrator(
        core,
        grace_period=0.01,
        runtime_variables={"max_timeout": "0.05"},
        register_phases={"WaitingPhase": WaitingPhase},
        checkpoint_path=checkpoint_path,
    )

    orchestrator.run()

    checkpoint = CheckpointManager(checkpoint_path).read()["waiting"]
    assert isinstance(checkpoint, CancelledCheckpoint)
    assert checkpoint.reason == "Orchestrator exceeded max_timeout of 0.05s"


def test_run_raises_runtime_error_when_phase_fails(tmp_path, make_orchestrator):
    """Full pipeline: a failing phase must cause run() to raise FatalProcessingError.

    A custom ``FailingPhase`` is discovered and registered by the composition root, validated by
    the engine, then driven by the orchestrator.
    """
    failing_core = tmp_path / "failing_core"
    write(
        failing_core / "agents" / "writer.md",
        "---\ntype: agent\nname: writer\nmodel: sonnet\n---\nsystem prompt",
    )
    write(
        failing_core / "f.yaml",
        "- type: phase\n  config:\n    name: failing\n    class: FailingPhase\n    agent: writer\n"
        "    tasks:\n      - name: t1\n        prompt: do it\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: failing\n",
    )

    class FailingPhase(Phase):
        async def execute(self, context):
            raise RuntimeError("intentional failure")

    orchestrator, _, _ = make_orchestrator(
        failing_core, grace_period=0.1, register_phases={"FailingPhase": FailingPhase}
    )

    with pytest.raises(FatalProcessingError, match="Phase 'failing' failed"):
        orchestrator.run()

    assert orchestrator.outcome is not None
    assert orchestrator.outcome.verdict is RunVerdict.FAILED
    assert orchestrator.outcome.failed_phase == "failing"
    assert orchestrator.outcome.error_type == "RuntimeError"


def test_run_records_normal_incomplete_return_as_timeout(tmp_path, make_orchestrator):
    core = tmp_path / "timeout_core"
    write(
        core / "f.yaml",
        "- type: phase\n  config:\n    name: slow\n    class: SlowPhase\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: slow\n",
    )

    class SlowPhase(Phase):
        async def execute(self, context):
            await asyncio.sleep(5)
            return PhaseOutcome(memory_text="too late")

    orchestrator, _, _ = make_orchestrator(
        core,
        grace_period=0.05,
        runtime_variables={"max_timeout": "0.2"},
        register_phases={"SlowPhase": SlowPhase},
    )

    orchestrator.run()

    assert orchestrator.outcome is not None
    assert orchestrator.outcome.verdict is RunVerdict.INCOMPLETE
    assert orchestrator.outcome.failure_kind is FailureKind.TIMEOUT
    assert orchestrator.outcome.phases[0].status is PhaseReportStatus.CANCELLED
    assert orchestrator.outcome.phases[0].cancellation_reason == "Orchestrator exceeded max_timeout of 0.2s"


async def test_cancelled_run_does_not_record_outcome(tmp_path, make_orchestrator):
    core = tmp_path / "cancelled_core"
    write(
        core / "f.yaml",
        "- type: phase\n  config:\n    name: slow\n    class: SlowPhase\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: slow\n",
    )

    class SlowPhase(Phase):
        async def execute(self, context):
            await asyncio.sleep(5)
            return PhaseOutcome(memory_text="too late")

    orchestrator, _, _ = make_orchestrator(
        core,
        grace_period=0.1,
        register_phases={"SlowPhase": SlowPhase},
    )
    task = asyncio.create_task(orchestrator.run_async())
    await asyncio.sleep(0.05)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert orchestrator.outcome is None
    assert not (tmp_path / "run.yaml").exists()


@pytest.mark.parametrize("failure_point", ["build", "persist"])
def test_outcome_recording_failure_does_not_mask_run_failure(tmp_path, make_orchestrator, monkeypatch, failure_point):
    core = tmp_path / "outcome_failure_core"
    write(
        core / "f.yaml",
        "- type: phase\n  config:\n    name: failing\n    class: FailingPhase\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: failing\n",
    )

    class FailingPhase(Phase):
        async def execute(self, context):
            raise RuntimeError("original failure")

    orchestrator, _, _ = make_orchestrator(
        core,
        grace_period=0.1,
        register_phases={"FailingPhase": FailingPhase},
    )
    if failure_point == "build":
        monkeypatch.setattr(
            orchestrator,
            "_current_run_checkpoints",
            MagicMock(side_effect=OSError("checkpoint unreadable")),
        )
    else:
        monkeypatch.setattr(orchestrator._outcome_store, "write", MagicMock(side_effect=OSError("disk full")))

    with pytest.raises(FatalProcessingError, match="original failure") as exc_info:
        orchestrator.run()

    operation = "build" if failure_point == "build" else "persist"
    detail = "checkpoint unreadable" if failure_point == "build" else "disk full"
    assert exc_info.value.__notes__ == [
        f"Outcome recording also failed: Failed to {operation} the flow outcome: {detail}"
    ]


async def test_outcome_build_failure_after_success_is_reported_distinctly(core_dir, make_orchestrator, monkeypatch):
    orchestrator, _, _ = make_orchestrator(core_dir)
    orchestrator._started_at = datetime.now(UTC)
    monkeypatch.setattr(
        orchestrator,
        "_current_run_checkpoints",
        MagicMock(side_effect=OSError("checkpoint unreadable")),
    )

    with pytest.raises(RunOutcomeBuildError, match="checkpoint unreadable"):
        await orchestrator._record_outcome(None)

    assert orchestrator.outcome is None


async def test_outcome_persistence_failure_retains_and_publishes_outcome(
    tmp_path, core_dir, make_orchestrator, monkeypatch
):
    callback_set = CallbackSet()
    finished: list[RunOutcome] = []

    @callback_set.on_run_finished
    async def on_run_finished(outcome: RunOutcome) -> None:
        finished.append(outcome)

    orchestrator, _, _ = make_orchestrator(core_dir, callbacks=Callbacks([callback_set]))
    orchestrator._started_at = datetime.now(UTC)
    monkeypatch.setattr(orchestrator._outcome_store, "write", MagicMock(side_effect=OSError("disk full")))

    with pytest.raises(RunOutcomePersistenceError, match="disk full"):
        await orchestrator._record_outcome(None)

    assert orchestrator.outcome is not None
    assert orchestrator.outcome.verdict is RunVerdict.INCOMPLETE
    assert finished == [orchestrator.outcome]
    assert not (tmp_path / "run.yaml").exists()


def test_current_run_checkpoints_excludes_stale_checkpoint(core_dir, make_orchestrator):
    orchestrator, _, _ = make_orchestrator(core_dir)
    orchestrator._checkpoint_manager.write_phase_checkpoint(
        "a",
        make_checkpoint(
            CheckpointStatus.SUCCESS,
            {
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:01:00+00:00",
            },
        ),
    )

    checkpoints = orchestrator._current_run_checkpoints(datetime(2026, 1, 2, tzinfo=UTC))

    assert checkpoints == {}


async def test_invalid_checkpoint_timestamp_fails_outcome_build(core_dir, make_orchestrator):
    orchestrator, _, _ = make_orchestrator(core_dir)
    orchestrator._started_at = datetime.now(UTC)
    orchestrator._checkpoint_manager.write_phase_checkpoint(
        "a",
        make_checkpoint(CheckpointStatus.SUCCESS, {"finished_at": "not-a-timestamp"}),
    )

    with pytest.raises(RunOutcomeBuildError, match="invalid finished_at timestamp 'not-a-timestamp'"):
        await orchestrator._record_outcome(None)

    assert orchestrator.outcome is None


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize — resume
# ---------------------------------------------------------------------------


@pytest.fixture
def linear_flow(tmp_path):
    """Three-phase linear flow: a -> b -> c."""
    write(tmp_path / "agents" / "writer.md", "---\ntype: agent\nname: writer\nmodel: sonnet\n---\nsystem prompt")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: a\n    agent: writer\n"
        "    tasks:\n      - name: ta\n        prompt: a\n"
        "- type: phase\n  config:\n    name: b\n    agent: writer\n"
        "    tasks:\n      - name: tb\n        prompt: b\n"
        "- type: phase\n  config:\n    name: c\n    agent: writer\n"
        "    tasks:\n      - name: tc\n        prompt: c\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: a\n      - phase: b\n        dependencies: [a]\n"
        "      - phase: c\n        dependencies: [b]\n",
    )
    return tmp_path


def _write_checkpoints(flow_dir: Path, statuses: dict[str, dict]) -> None:
    manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    for phase_id, data in statuses.items():
        manager.write_phase_checkpoint(phase_id, make_checkpoint(CheckpointStatus(data["status"]), data))


def _drain_trigger_phase_ids(orchestrator) -> list:
    ids = []
    while not orchestrator._queue.empty():
        msg = orchestrator._queue.get_nowait()
        if isinstance(msg, PhaseTrigger):
            ids.append(msg.phase_id)
    return ids


async def test_resume_skips_completed_phases(linear_flow, make_orchestrator):
    """With a,b succeeded, only c is registered to run."""
    _write_checkpoints(linear_flow, {"a": {"status": "success"}, "b": {"status": "success"}})
    orchestrator, _, _ = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    assert {p.name for p in processors} == {"c"}


async def test_resume_marks_only_frontier_phase(linear_flow, make_orchestrator):
    """The first non-completed phase is the frontier; nothing else is."""
    _write_checkpoints(linear_flow, {"a": {"status": "success"}, "b": {"status": "success"}})
    orchestrator, _, _ = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    phases_by_name = {p.name: p for p in orchestrator._subscribers.get(PhaseTrigger, [])}
    assert phases_by_name["c"]._is_resume_frontier is True


async def test_resume_emits_triggers_for_completed_phases(linear_flow, make_orchestrator):
    """Completed phases get their completion triggers emitted so dependents unblock."""
    _write_checkpoints(linear_flow, {"a": {"status": "success"}, "b": {"status": "success"}})
    orchestrator, _, _ = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    ids = _drain_trigger_phase_ids(orchestrator)
    assert None in ids  # initial trigger
    assert {i for i in ids if i is not None} == {"a", "b"}


async def test_resume_dependency_closure_reruns_descendants_of_failure(linear_flow, make_orchestrator):
    """A succeeded phase whose ancestor failed is NOT skipped — it and its descendants re-run."""
    _write_checkpoints(
        linear_flow,
        {"a": {"status": "failed", "error": "boom"}, "b": {"status": "success"}, "c": {"status": "success"}},
    )
    orchestrator, _, _ = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    phases_by_name = {p.name: p for p in orchestrator._subscribers.get(PhaseTrigger, [])}
    assert set(phases_by_name) == {"a", "b", "c"}  # nothing skipped
    assert phases_by_name["a"]._is_resume_frontier is True
    assert phases_by_name["b"]._is_resume_frontier is False
    assert phases_by_name["c"]._is_resume_frontier is False


async def test_resume_with_no_checkpoints_frontier_is_root(linear_flow, make_orchestrator):
    """Ctrl+C before any checkpoint: all phases run, the root is the frontier."""
    orchestrator, _, _ = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    phases_by_name = {p.name: p for p in orchestrator._subscribers.get(PhaseTrigger, [])}
    assert set(phases_by_name) == {"a", "b", "c"}
    assert phases_by_name["a"]._is_resume_frontier is True
    assert phases_by_name["b"]._is_resume_frontier is False
    assert phases_by_name["c"]._is_resume_frontier is False


async def test_no_resume_ignores_checkpoints(linear_flow, make_orchestrator):
    """Without resume, every phase is registered and none is a frontier, despite checkpoints."""
    _write_checkpoints(linear_flow, {"a": {"status": "success"}, "b": {"status": "success"}})
    orchestrator, _, _ = make_orchestrator(linear_flow, resume=False)
    await orchestrator.on_initialize()

    phases_by_name = {p.name: p for p in orchestrator._subscribers.get(PhaseTrigger, [])}
    assert set(phases_by_name) == {"a", "b", "c"}
    assert all(p._is_resume_frontier is False for p in phases_by_name.values())
    ids = _drain_trigger_phase_ids(orchestrator)
    assert ids == [None]  # only the initial trigger, no resume triggers


async def test_resume_corrupt_checkpoints_raises_flow_config_error(linear_flow, make_orchestrator):
    (linear_flow / "checkpoints.yaml").write_text("{ not: valid: yaml", encoding="utf-8")
    orchestrator, _, _ = make_orchestrator(linear_flow, resume=True)
    with pytest.raises(ConfigError, match="Cannot resume"):
        await orchestrator.on_initialize()


async def test_resume_closure_independent_of_flow_declaration_order(tmp_path, make_orchestrator):
    """A flow declared dependents-first still resolves the resume closure correctly."""
    write(tmp_path / "agents" / "writer.md", "---\ntype: agent\nname: writer\nmodel: sonnet\n---\nsystem prompt")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: a\n    agent: writer\n"
        "    tasks:\n      - name: ta\n        prompt: a\n"
        "- type: phase\n  config:\n    name: b\n    agent: writer\n"
        "    tasks:\n      - name: tb\n        prompt: b\n"
        "- type: phase\n  config:\n    name: c\n    agent: writer\n"
        "    tasks:\n      - name: tc\n        prompt: c\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: c\n        dependencies: [b]\n"
        "      - phase: b\n        dependencies: [a]\n"
        "      - phase: a\n",
    )
    _write_checkpoints(tmp_path, {"a": {"status": "success"}, "b": {"status": "success"}})
    orchestrator, _, _ = make_orchestrator(tmp_path, resume=True)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    assert {p.name for p in processors} == {"c"}  # a and b skipped, c is the frontier
    assert processors[0]._is_resume_frontier is True


async def test_finalization_persists_generating_before_awaiting_summary(core_dir, make_orchestrator, tmp_path):
    events: list[str] = []
    callback_set = CallbackSet()
    checkpoint_path = tmp_path / "finalization-checkpoints.yaml"

    @callback_set.on_run_finalizing
    async def on_run_finalizing(outcome: RunOutcome) -> None:
        persisted = RunOutcomeStore(tmp_path / "run.yaml").read()
        assert outcome.summary.status is RunSummaryStatus.GENERATING
        assert persisted.summary.status is RunSummaryStatus.GENERATING
        events.append("finalizing")

    @callback_set.on_run_finished
    async def on_run_finished(outcome: RunOutcome) -> None:
        events.append("finished")

    class FakeSummarizer:
        async def summarize(self, outcome: RunOutcome) -> RunSummaryAttempt:
            events.append("summarize")
            return RunSummaryAttempt(
                metadata=RunSummaryMetadata(status=RunSummaryStatus.SUCCEEDED, markdown_path="summary.md")
            )

    orchestrator, _, _ = make_orchestrator(
        core_dir,
        checkpoint_path=checkpoint_path,
        callbacks=Callbacks([callback_set]),
    )
    orchestrator._resources = MagicMock()
    orchestrator._started_at = datetime.now(UTC)
    orchestrator._build_run_summarizer = lambda: FakeSummarizer()

    await orchestrator._record_outcome(None)

    assert events == ["finalizing", "summarize", "finished"]
    assert orchestrator.outcome is not None
    assert orchestrator.outcome.summary.status is RunSummaryStatus.SUCCEEDED


async def test_summary_only_cancellation_finishes_with_deterministic_outcome(core_dir, make_orchestrator):
    started = asyncio.Event()
    finished: list[RunOutcome] = []
    callback_set = CallbackSet()

    @callback_set.on_run_finished
    async def on_run_finished(outcome: RunOutcome) -> None:
        finished.append(outcome)

    class WaitingSummarizer:
        async def summarize(self, outcome: RunOutcome) -> RunSummaryAttempt:
            started.set()
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    orchestrator, _, _ = make_orchestrator(core_dir, callbacks=Callbacks([callback_set]))
    orchestrator._resources = MagicMock()
    orchestrator._started_at = datetime.now(UTC)
    orchestrator._build_run_summarizer = lambda: WaitingSummarizer()

    finalization = asyncio.create_task(orchestrator._record_outcome(None))
    await started.wait()
    orchestrator.request_summary_cancellation()
    await finalization

    assert orchestrator.outcome is not None
    assert orchestrator.outcome.summary.status is RunSummaryStatus.UNAVAILABLE
    assert "stopped by the user" in (orchestrator.outcome.summary.error or "")
    assert finished == [orchestrator.outcome]


async def test_orchestrator_task_cancellation_during_summary_propagates(core_dir, make_orchestrator):
    started = asyncio.Event()
    callback_set = CallbackSet()
    finished: list[RunOutcome] = []

    @callback_set.on_run_finished
    async def on_run_finished(outcome: RunOutcome) -> None:
        finished.append(outcome)

    class WaitingSummarizer:
        async def summarize(self, outcome: RunOutcome) -> RunSummaryAttempt:
            started.set()
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    orchestrator, _, _ = make_orchestrator(core_dir, callbacks=Callbacks([callback_set]))
    orchestrator._resources = MagicMock()
    orchestrator._started_at = datetime.now(UTC)
    orchestrator._build_run_summarizer = lambda: WaitingSummarizer()

    finalization = asyncio.create_task(orchestrator._record_outcome(None))
    await started.wait()
    finalization.cancel()

    with pytest.raises(asyncio.CancelledError):
        await finalization
    persisted = RunOutcomeStore(orchestrator._checkpoint_manager.outcome_path).read()
    assert persisted.summary.status is RunSummaryStatus.UNAVAILABLE
    assert "interrupted" in (persisted.summary.error or "")
    assert orchestrator.outcome == persisted
    assert finished == []


async def test_summary_cancellation_requested_before_child_creation_is_honored(core_dir, make_orchestrator):
    class WaitingSummarizer:
        async def summarize(self, outcome: RunOutcome) -> RunSummaryAttempt:
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    orchestrator, _, _ = make_orchestrator(core_dir)
    orchestrator._resources = MagicMock()
    orchestrator._build_run_summarizer = lambda: WaitingSummarizer()
    orchestrator.request_summary_cancellation()
    outcome = RunOutcome.model_construct(flow_name="demo")

    attempt = await orchestrator._summarize_outcome(outcome, datetime.now(UTC))

    assert attempt.metadata.status is RunSummaryStatus.UNAVAILABLE
    assert "stopped by the user" in (attempt.metadata.error or "")
