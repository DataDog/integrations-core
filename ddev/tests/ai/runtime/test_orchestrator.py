# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from pathlib import Path
from textwrap import dedent
from typing import Any
from unittest.mock import MagicMock

import pytest

from ddev.ai.config.engine import ConfigurationEngine
from ddev.ai.config.errors import FlowConfigError
from ddev.ai.phases.base import Phase
from ddev.ai.phases.loader import PhaseLoader
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.runtime.orchestrator import PhaseOrchestrator
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError


FLOW_NAME = "test_flow"


def make_engine(tmp_path: Path, yaml_content: str) -> ConfigurationEngine:
    flow_dir = tmp_path / FLOW_NAME
    flow_dir.mkdir(exist_ok=True)
    (flow_dir / "flow.yaml").write_text(yaml_content)
    return ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)


@pytest.fixture
def file_access_policy(tmp_path) -> FileAccessPolicy:
    return FileAccessPolicy(write_root=tmp_path)


@pytest.fixture
def make_orchestrator(file_access_policy: FileAccessPolicy, tmp_path: Path):
    """Factory that builds a PhaseOrchestrator with test defaults."""

    def _make(engine: ConfigurationEngine | None = None, **overrides: Any) -> PhaseOrchestrator:
        _engine = engine or ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
        kwargs: dict[str, Any] = {
            "engine": _engine,
            "phase_loader": PhaseLoader(),
            "checkpoint_path": tmp_path / "checkpoints.yaml",
            "runtime_variables": {},
            "agent_clients": {"anthropic": MagicMock()},
            "file_access_policy": file_access_policy,
            **overrides,
        }
        return PhaseOrchestrator(**kwargs)

    return _make


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
    flow_dir = tmp_path / FLOW_NAME
    flow_dir.mkdir()
    prompts_dir = flow_dir / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "writer.md").write_text("system prompt")
    (flow_dir / "flow.yaml").write_text(
        dedent("""\
        - type: agent
          config:
            name: writer
            system_prompt_path: prompts/writer.md
        - type: phase
          config:
            name: a
            class: AgenticPhase
            agent: writer
            tasks:
              - name: task_a
                prompt: task a
        - type: phase
          config:
            name: b
            class: AgenticPhase
            agent: writer
            tasks:
              - name: task_b
                prompt: task b
        - type: flow
          config:
            name: test_flow
            flow:
              - phase: a
              - phase: b
                dependencies: [a]
    """)
    )
    return ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)


async def test_on_initialize_registers_all_flow_phases(minimal_flow, make_orchestrator):
    orchestrator = make_orchestrator(engine=minimal_flow)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    phase_names = {p.name for p in processors}
    assert phase_names == {"a", "b"}


async def test_on_initialize_wires_dependencies(minimal_flow, make_orchestrator):
    orchestrator = make_orchestrator(engine=minimal_flow)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    phases_by_name = {p.name: p for p in processors}
    assert phases_by_name["a"]._remaining_dependencies == set()
    assert phases_by_name["b"]._remaining_dependencies == {"a"}


async def test_on_initialize_submits_initial_phase_trigger(minimal_flow, make_orchestrator):
    orchestrator = make_orchestrator(engine=minimal_flow)
    await orchestrator.on_initialize()

    assert not orchestrator._queue.empty()
    msg = orchestrator._queue.get_nowait()
    assert isinstance(msg, PhaseTrigger)
    assert msg.phase_id is None


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize — orphan-phase validation
# ---------------------------------------------------------------------------


async def test_orphan_phase_with_unknown_type_does_not_block_init(tmp_path, make_orchestrator):
    """A phase defined in the resource list but absent from flow: may have an unknown class — no error."""
    (tmp_path / FLOW_NAME / "prompts").mkdir(parents=True, exist_ok=True)
    (tmp_path / FLOW_NAME / "prompts" / "writer.md").write_text("system prompt")
    engine = make_engine(
        tmp_path,
        dedent("""\
        - type: agent
          config:
            name: writer
            system_prompt_path: prompts/writer.md
        - type: phase
          config:
            name: real
            class: AgenticPhase
            agent: writer
            tasks:
              - name: t1
                prompt: do it
        - type: phase
          config:
            name: orphan
            class: BogusType
            agent: writer
            tasks:
              - name: t2
                prompt: ignored
        - type: flow
          config:
            name: test_flow
            flow:
              - phase: real
        """),
    )
    orchestrator = make_orchestrator(engine=engine)
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    assert {p.name for p in processors} == {"real"}



# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_finalize
# ---------------------------------------------------------------------------


async def test_on_finalize_no_failure_is_noop(make_orchestrator):
    orchestrator = make_orchestrator()
    await orchestrator.on_finalize(None)  # must not raise


async def test_on_finalize_after_phase_failed_logs(make_orchestrator, caplog):
    orchestrator = make_orchestrator()
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="boom")
    exc = FatalProcessingError("Phase 'p1' failed: boom")
    with pytest.raises(FatalProcessingError):
        await orchestrator.on_message_received(msg)

    with caplog.at_level(logging.ERROR):
        await orchestrator.on_finalize(exc)  # must not raise

    assert any("Pipeline aborted" in r.message and "p1" in r.message and "boom" in r.message for r in caplog.records)


async def test_on_finalize_no_exception_no_log(make_orchestrator, caplog):
    orchestrator = make_orchestrator()
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="boom")
    with pytest.raises(FatalProcessingError):
        await orchestrator.on_message_received(msg)

    with caplog.at_level(logging.ERROR):
        await orchestrator.on_finalize(None)  # exception=None means clean exit — no log

    assert not any("Pipeline aborted" in r.message for r in caplog.records)


def test_run_raises_runtime_error_when_phase_fails(tmp_path, make_orchestrator, file_access_policy):
    """Full pipeline: a failing phase must cause run() to raise RuntimeError."""
    (tmp_path / FLOW_NAME / "prompts").mkdir(parents=True, exist_ok=True)
    (tmp_path / FLOW_NAME / "prompts" / "writer.md").write_text("system prompt")
    engine = make_engine(
        tmp_path,
        dedent("""\
        - type: agent
          config:
            name: writer
            system_prompt_path: prompts/writer.md
        - type: phase
          config:
            name: failing
            class: FailingPhase
            agent: writer
            tasks:
              - name: t1
                prompt: do it
        - type: flow
          config:
            name: test_flow
            flow:
              - phase: failing
        """),
    )

    class FailingPhase(Phase):
        async def execute(self, context):
            raise RuntimeError("intentional failure")

    class _FailingPhaseLoader(PhaseLoader):
        def _discover(self, registry, flow_name):
            super()._discover(registry, flow_name)
            registry.register("FailingPhase", FailingPhase)

    orchestrator = make_orchestrator(
        engine=engine,
        phase_loader=_FailingPhaseLoader(),
        grace_period=0.1,
    )

    with pytest.raises(FatalProcessingError, match="Phase 'failing' failed"):
        orchestrator.run()
