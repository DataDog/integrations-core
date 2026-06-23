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
from ddev.ai.config.engine import ConfigurationEngine
from ddev.ai.config.errors import FlowConfigError
from ddev.ai.phases.base import Phase
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.runtime.orchestrator import PhaseOrchestrator
from ddev.ai.runtime.resources import RunResources
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
def make_orchestrator(file_access_policy, tmp_path):
    """Factory that builds a PhaseOrchestrator with test defaults."""

    def _make(engine: ConfigurationEngine | None = None, **overrides: Any) -> PhaseOrchestrator:
        kwargs: dict[str, Any] = {
            "engine": engine or ConfigurationEngine(FLOW_NAME, core_dir=tmp_path),
            "checkpoint_path": tmp_path / "checkpoints.yaml",
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
    o1 = make_orchestrator()
    o2 = make_orchestrator()

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


async def test_on_initialize_unknown_phase_type_raises_flow_config_error(tmp_path, make_orchestrator):
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
            name: a
            class: NotARealPhase
            agent: writer
            tasks:
              - name: task_a
                prompt: task a
        - type: flow
          config:
            name: test_flow
            flow:
              - phase: a
        """),
    )
    orchestrator = make_orchestrator(engine=engine)
    with pytest.raises(FlowConfigError, match="Unknown phase type"):
        await orchestrator.on_initialize()


async def test_on_initialize_missing_agent_raises(tmp_path, make_orchestrator):
    (tmp_path / FLOW_NAME / "prompts").mkdir(parents=True, exist_ok=True)
    with pytest.raises(FlowConfigError):
        engine = make_engine(
            tmp_path,
            dedent("""\
            - type: agent
              config:
                name: writer
                system_prompt_path: prompts/writer.md
            - type: phase
              config:
                name: a
                class: AgenticPhase
                agent: nonexistent_agent
                tasks:
                  - name: task_a
                    prompt: task a
            - type: flow
              config:
                name: test_flow
                flow:
                  - phase: a
            """),
        )
        orchestrator = make_orchestrator(engine=engine)
        await orchestrator.on_initialize()


async def test_file_registry_getter_is_idempotent(minimal_flow, make_orchestrator):
    orchestrator = make_orchestrator(engine=minimal_flow)
    await orchestrator.on_initialize()
    assert orchestrator._resources is not None
    assert orchestrator._resources.file_registry is orchestrator._resources.file_registry


def test_resource_provider_agent_config_unknown_name_raises(file_access_policy):
    from ddev.ai.config.models import AgentConfig

    provider = RunResources(
        agent_clients={},
        file_access_policy=file_access_policy,
        agents={
            "a": AgentConfig(name="a"),
            "b": AgentConfig(name="b"),
        },
        callbacks=Callbacks(),
    )
    with pytest.raises(ResourceUnavailableError, match="No agent definition named 'missing'"):
        provider.agent_config("missing")


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


async def test_phase_in_flow_with_unknown_type_raises(tmp_path, make_orchestrator):
    """A phase referenced from flow: with an unknown class must raise FlowConfigError."""
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
            name: a
            class: NotARealPhase
            agent: writer
            tasks:
              - name: t1
                prompt: do it
        - type: flow
          config:
            name: test_flow
            flow:
              - phase: a
        """),
    )
    orchestrator = make_orchestrator(engine=engine)
    with pytest.raises(FlowConfigError, match="Unknown phase type"):
        await orchestrator.on_initialize()


async def test_orphan_phase_logs_warning(tmp_path, make_orchestrator, caplog):
    """A phase defined in the resource list but not in flow runs without error."""
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
            class: AgenticPhase
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
    with caplog.at_level(logging.WARNING):
        await orchestrator.on_initialize()  # must not raise

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    assert {p.name for p in processors} == {"real"}


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize — validate_config invocation
# ---------------------------------------------------------------------------


async def test_on_initialize_invokes_validate_config(tmp_path, make_orchestrator):
    """validate_config is called for each scheduled phase; raising propagates as FlowConfigError."""
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
            name: a
            class: AgenticPhase
            agent: writer
            tasks: []
        - type: flow
          config:
            name: test_flow
            flow:
              - phase: a
        """),
    )
    orchestrator = make_orchestrator(engine=engine)
    with pytest.raises(FlowConfigError, match="at least one task"):
        await orchestrator.on_initialize()


async def test_on_initialize_skips_validate_config_for_orphan(tmp_path, make_orchestrator):
    """A phase defined but not in flow must not trigger its validate_config."""
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
            class: AgenticPhase
            agent: writer
            tasks: []
        - type: flow
          config:
            name: test_flow
            flow:
              - phase: real
        """),
    )
    orchestrator = make_orchestrator(engine=engine)
    await orchestrator.on_initialize()  # must not raise


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

    orchestrator = make_orchestrator(engine=engine, grace_period=0.1)
    orchestrator._phase_registry.register("FailingPhase", FailingPhase)

    with pytest.raises(FatalProcessingError, match="Phase 'failing' failed"):
        orchestrator.run()
