# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest.mock import MagicMock

import pytest

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.base import Phase
from ddev.ai.phases.config import FlowConfigError
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.runtime.orchestrator import PhaseOrchestrator
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError


@pytest.fixture
def file_access_policy(tmp_path) -> FileAccessPolicy:
    return FileAccessPolicy(write_root=tmp_path)


@pytest.fixture
def make_orchestrator(file_access_policy):
    """Factory that builds a PhaseOrchestrator with test defaults.

    Pass a ``base_dir`` to anchor ``flow.yaml`` / ``checkpoints.yaml`` (defaults to
    ``/fake`` for tests that never touch disk). Any constructor kwarg can be overridden.
    """

    def _make(base_dir: Path | None = None, **overrides: Any) -> PhaseOrchestrator:
        base_dir = base_dir if base_dir is not None else Path("/fake")
        kwargs: dict[str, Any] = {
            "flow_yaml_path": base_dir / "flow.yaml",
            "checkpoint_path": base_dir / "checkpoints.yaml",
            "runtime_variables": {},
            "agent_clients": {"anthropic": MagicMock()},
            "file_access_policy": file_access_policy,
            **overrides,
        }
        return PhaseOrchestrator(**kwargs)

    return _make


# ---------------------------------------------------------------------------
# PhaseOrchestrator registry ownership
# ---------------------------------------------------------------------------


def test_two_orchestrators_have_independent_registries(tmp_path, make_orchestrator):
    """Each PhaseOrchestrator owns its own registry; registering in one does not affect the other."""
    o1 = make_orchestrator(tmp_path)
    o2 = make_orchestrator(tmp_path)

    class ExclusivePhase(Phase):
        pass

    o1._phase_registry.register("ExclusivePhase", ExclusivePhase)
    assert "ExclusivePhase" in o1._phase_registry.known_names()
    assert "ExclusivePhase" not in o2._phase_registry.known_names()


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_message_received
# ---------------------------------------------------------------------------


async def test_on_message_received_fatal_on_phase_failed(make_orchestrator):
    orchestrator = make_orchestrator()
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="something broke")

    with pytest.raises(FatalProcessingError, match="Phase 'p1' failed"):
        await orchestrator.on_message_received(msg)


async def test_on_message_received_ignores_other_messages(make_orchestrator):
    orchestrator = make_orchestrator()
    # These should not raise
    await orchestrator.on_message_received(PhaseTrigger(id="start", phase_id=None))
    await orchestrator.on_message_received(PhaseTrigger(id="f1", phase_id="p1"))


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_flow(tmp_path):
    """Two-phase flow: 'a' is root, 'b' depends on 'a'."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          a:
            agent: writer
            tasks:
              - name: task_a
                prompt: task a
          b:
            agent: writer
            tasks:
              - name: task_b
                prompt: task b
        flow:
          - phase: a
          - phase: b
            dependencies: [a]
        """)
    )
    return tmp_path


async def test_on_initialize_registers_all_flow_phases(minimal_flow, make_orchestrator):
    orchestrator = make_orchestrator(minimal_flow)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    phase_names = {p.name for p in processors}
    assert phase_names == {"a", "b"}


async def test_on_initialize_wires_dependencies(minimal_flow, make_orchestrator):
    orchestrator = make_orchestrator(minimal_flow)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    phases_by_name = {p.name: p for p in processors}
    assert phases_by_name["a"]._remaining_dependencies == set()
    assert phases_by_name["b"]._remaining_dependencies == {"a"}


async def test_on_initialize_submits_initial_phase_trigger(minimal_flow, make_orchestrator):
    orchestrator = make_orchestrator(minimal_flow)
    await orchestrator.on_initialize()

    assert not orchestrator._queue.empty()
    msg = orchestrator._queue.get_nowait()
    assert isinstance(msg, PhaseTrigger)
    assert msg.phase_id is None


async def test_on_initialize_unknown_phase_type_raises_flow_config_error(tmp_path, make_orchestrator):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          a:
            type: NotARealPhase
            agent: writer
            tasks:
              - name: task_a
                prompt: task a
        flow:
          - phase: a
        """)
    )
    orchestrator = make_orchestrator(tmp_path)
    with pytest.raises(FlowConfigError, match="Unknown phase type"):
        await orchestrator.on_initialize()


async def test_on_initialize_flow_phases_dir_outside_ai_root_raises(tmp_path, make_orchestrator):
    """phases/ directory outside the ddev.ai package tree raises FlowConfigError."""
    (tmp_path / "phases").mkdir()
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          a:
            agent: writer
            tasks:
              - name: t1
                prompt: do it
        flow:
          - phase: a
        """)
    )
    orchestrator = make_orchestrator(tmp_path)
    with pytest.raises(FlowConfigError, match="ddev.ai package tree"):
        await orchestrator.on_initialize()


async def test_on_initialize_missing_agent_raises(tmp_path, make_orchestrator):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          a:
            agent: nonexistent_agent
            tasks:
              - name: task_a
                prompt: task a
        flow:
          - phase: a
        """)
    )
    orchestrator = make_orchestrator(tmp_path)
    with pytest.raises(FlowConfigError):
        await orchestrator.on_initialize()


async def test_file_registry_getter_is_idempotent(minimal_flow, make_orchestrator):
    orchestrator = make_orchestrator(minimal_flow)
    await orchestrator.on_initialize()
    assert orchestrator._resources is not None
    assert orchestrator._resources.file_registry is orchestrator._resources.file_registry


def test_resource_provider_agent_config_unknown_name_raises(file_access_policy):
    provider = RunResources(
        agent_clients={},
        file_access_policy=file_access_policy,
        agents={"a": MagicMock(), "b": MagicMock()},
        callbacks=Callbacks(),
    )
    with pytest.raises(ResourceUnavailableError, match="No agent definition named 'missing'"):
        provider.agent_config("missing")


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize — orphan-phase validation
# ---------------------------------------------------------------------------


async def test_orphan_phase_with_unknown_type_does_not_block_init(tmp_path, make_orchestrator):
    """A phase defined in phases: but absent from flow: may have an unknown type — no error."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          real:
            agent: writer
            tasks:
              - name: t1
                prompt: do it
          orphan:
            type: BogusType
            agent: writer
            tasks:
              - name: t2
                prompt: ignored
        flow:
          - phase: real
        """)
    )
    orchestrator = make_orchestrator(tmp_path)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    assert {p.name for p in processors} == {"real"}


async def test_phase_in_flow_with_unknown_type_raises(tmp_path, make_orchestrator):
    """A phase referenced from flow: with an unknown type must still raise FlowConfigError."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          a:
            type: NotARealPhase
            agent: writer
            tasks:
              - name: t1
                prompt: do it
        flow:
          - phase: a
        """)
    )
    orchestrator = make_orchestrator(tmp_path)
    with pytest.raises(FlowConfigError, match="Unknown phase type"):
        await orchestrator.on_initialize()


async def test_orphan_phase_logs_warning(tmp_path, make_orchestrator, caplog):
    """An orphan phase must emit a warning containing its phase id."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          real:
            agent: writer
            tasks:
              - name: t1
                prompt: do it
          orphan:
            agent: writer
            tasks:
              - name: t2
                prompt: ignored
        flow:
          - phase: real
        """)
    )
    orchestrator = make_orchestrator(tmp_path)
    with caplog.at_level(logging.WARNING):
        await orchestrator.on_initialize()

    assert any("orphan" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize — validate_config invocation
# ---------------------------------------------------------------------------


async def test_on_initialize_invokes_validate_config(tmp_path, make_orchestrator):
    """validate_config is called for each scheduled phase; raising propagates as FlowConfigError."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          a:
            agent: writer
            tasks: []
        flow:
          - phase: a
        """)
    )
    orchestrator = make_orchestrator(tmp_path)
    with pytest.raises(FlowConfigError, match="at least one task"):
        await orchestrator.on_initialize()


async def test_on_initialize_skips_validate_config_for_orphan(tmp_path, make_orchestrator):
    """A phase defined but not in flow must not trigger its validate_config."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          real:
            agent: writer
            tasks:
              - name: t1
                prompt: do it
          orphan:
            agent: writer
            tasks: []
        flow:
          - phase: real
        """)
    )
    orchestrator = make_orchestrator(tmp_path)
    await orchestrator.on_initialize()  # must not raise


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_finalize
# ---------------------------------------------------------------------------


async def test_on_finalize_no_failure_is_noop(tmp_path, make_orchestrator):
    orchestrator = make_orchestrator()
    await orchestrator.on_finalize(None)  # must not raise


async def test_on_finalize_after_phase_failed_logs(tmp_path, make_orchestrator, caplog):
    orchestrator = make_orchestrator()
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="boom")
    exc = FatalProcessingError("Phase 'p1' failed: boom")
    with pytest.raises(FatalProcessingError):
        await orchestrator.on_message_received(msg)

    with caplog.at_level(logging.ERROR):
        await orchestrator.on_finalize(exc)  # must not raise

    assert any("Pipeline aborted" in r.message and "p1" in r.message and "boom" in r.message for r in caplog.records)


async def test_on_finalize_no_exception_no_log(tmp_path, make_orchestrator, caplog):
    orchestrator = make_orchestrator()
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="boom")
    with pytest.raises(FatalProcessingError):
        await orchestrator.on_message_received(msg)

    with caplog.at_level(logging.ERROR):
        await orchestrator.on_finalize(None)  # exception=None means clean exit — no log

    assert not any("Pipeline aborted" in r.message for r in caplog.records)


def test_run_raises_runtime_error_when_phase_fails(tmp_path, make_orchestrator):
    """Full pipeline: a failing phase must cause run() to raise RuntimeError."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          failing:
            type: FailingPhase
            agent: writer
            tasks:
              - name: t1
                prompt: do it
        flow:
          - phase: failing
        """)
    )

    class FailingPhase(Phase):
        async def execute(self, context):
            raise RuntimeError("intentional failure")

    orchestrator = make_orchestrator(tmp_path, grace_period=0.1)
    orchestrator._phase_registry.register("FailingPhase", FailingPhase)

    with pytest.raises(FatalProcessingError, match="Phase 'failing' failed"):
        orchestrator.run()


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize — resume
# ---------------------------------------------------------------------------


@pytest.fixture
def linear_flow(tmp_path):
    """Three-phase linear flow: a -> b -> c."""
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          a:
            agent: writer
            tasks:
              - name: ta
                prompt: a
          b:
            agent: writer
            tasks:
              - name: tb
                prompt: b
          c:
            agent: writer
            tasks:
              - name: tc
                prompt: c
        flow:
          - phase: a
          - phase: b
            dependencies: [a]
          - phase: c
            dependencies: [b]
        """)
    )
    return tmp_path


def _write_checkpoints(flow_dir: Path, statuses: dict[str, dict]) -> None:
    manager = CheckpointManager(flow_dir / "checkpoints.yaml")
    for phase_id, data in statuses.items():
        manager.write_phase_checkpoint(phase_id, data)


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
    orchestrator = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    assert {p.name for p in processors} == {"c"}


async def test_resume_marks_only_frontier_phase(linear_flow, make_orchestrator):
    """The first non-completed phase is the frontier; nothing else is."""
    _write_checkpoints(linear_flow, {"a": {"status": "success"}, "b": {"status": "success"}})
    orchestrator = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    phases_by_name = {p.name: p for p in orchestrator._subscribers.get(PhaseTrigger, [])}
    assert phases_by_name["c"]._is_resume_frontier is True


async def test_resume_emits_triggers_for_completed_phases(linear_flow, make_orchestrator):
    """Completed phases get their completion triggers emitted so dependents unblock."""
    _write_checkpoints(linear_flow, {"a": {"status": "success"}, "b": {"status": "success"}})
    orchestrator = make_orchestrator(linear_flow, resume=True)
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
    orchestrator = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    phases_by_name = {p.name: p for p in orchestrator._subscribers.get(PhaseTrigger, [])}
    assert set(phases_by_name) == {"a", "b", "c"}  # nothing skipped
    assert phases_by_name["a"]._is_resume_frontier is True
    assert phases_by_name["b"]._is_resume_frontier is False
    assert phases_by_name["c"]._is_resume_frontier is False


async def test_resume_with_no_checkpoints_frontier_is_root(linear_flow, make_orchestrator):
    """Ctrl+C before any checkpoint: all phases run, the root is the frontier."""
    orchestrator = make_orchestrator(linear_flow, resume=True)
    await orchestrator.on_initialize()

    phases_by_name = {p.name: p for p in orchestrator._subscribers.get(PhaseTrigger, [])}
    assert set(phases_by_name) == {"a", "b", "c"}
    assert phases_by_name["a"]._is_resume_frontier is True
    assert phases_by_name["b"]._is_resume_frontier is False
    assert phases_by_name["c"]._is_resume_frontier is False


async def test_no_resume_ignores_checkpoints(linear_flow, make_orchestrator):
    """Without resume, every phase is registered and none is a frontier, despite checkpoints."""
    _write_checkpoints(linear_flow, {"a": {"status": "success"}, "b": {"status": "success"}})
    orchestrator = make_orchestrator(linear_flow, resume=False)
    await orchestrator.on_initialize()

    phases_by_name = {p.name: p for p in orchestrator._subscribers.get(PhaseTrigger, [])}
    assert set(phases_by_name) == {"a", "b", "c"}
    assert all(p._is_resume_frontier is False for p in phases_by_name.values())
    ids = _drain_trigger_phase_ids(orchestrator)
    assert ids == [None]  # only the initial trigger, no resume triggers


async def test_resume_corrupt_checkpoints_raises_flow_config_error(linear_flow, make_orchestrator):
    (linear_flow / "checkpoints.yaml").write_text("{ not: valid: yaml", encoding="utf-8")
    orchestrator = make_orchestrator(linear_flow, resume=True)
    with pytest.raises(FlowConfigError, match="Cannot resume"):
        await orchestrator.on_initialize()
