# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
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
from ddev.ai.runtime.checkpoints import CheckpointManager, CheckpointStatus
from ddev.ai.runtime.orchestrator import PhaseOrchestrator
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
    received: list[tuple[BaseException, str | None]] = []

    @callback_set.on_run_error
    async def handler(error: BaseException, phase_id: str | None) -> None:
        received.append((error, phase_id))

    orchestrator, _, _ = make_orchestrator(core_dir, callbacks=Callbacks([callback_set]))
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="something broke")

    with pytest.raises(FatalProcessingError):
        await orchestrator.on_message_received(msg)

    assert len(received) == 1
    assert isinstance(received[0][0], FatalProcessingError)
    assert received[0][1] == "p1"


async def test_on_error_fires_unscoped_run_error_callback(core_dir, make_orchestrator):
    callback_set = CallbackSet()
    received: list[tuple[BaseException, str | None]] = []

    @callback_set.on_run_error
    async def handler(error: BaseException, phase_id: str | None) -> None:
        received.append((error, phase_id))

    orchestrator, _, _ = make_orchestrator(core_dir, callbacks=Callbacks([callback_set]))
    original_error = RuntimeError("scheduler broke")
    wrapped = OrchestratorHookError(HookName.ON_INITIALIZE, original_error)

    with pytest.raises(FatalProcessingError):
        await orchestrator.on_error(wrapped)

    assert received == [(original_error, None)]


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize
# ---------------------------------------------------------------------------


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
    orchestrator, _, _ = make_orchestrator(
        core,
        grace_period=0.1,
        register_phases={"RecordingPhase": RecordingPhase},
        checkpoint_path=checkpoint_path,
    )

    orchestrator.run()  # must not raise

    assert executed == ["a", "b"]

    mgr = CheckpointManager(checkpoint_path)
    checkpoints = mgr.read()
    assert checkpoints["a"].status == CheckpointStatus.SUCCESS
    assert checkpoints["b"].status == CheckpointStatus.SUCCESS


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
