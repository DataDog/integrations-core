# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock

import pytest

from ddev.ai.phases.base import Phase, PhaseRegistry
from ddev.ai.phases.config import FlowConfigError
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.orchestrator import PhaseOrchestrator, _discover_and_register_phases
from ddev.event_bus.exceptions import FatalProcessingError

# ---------------------------------------------------------------------------
# _discover_and_register_phases
# ---------------------------------------------------------------------------


def test_discover_registers_phase_itself():
    registry = PhaseRegistry()
    _discover_and_register_phases(registry)
    assert "Phase" in registry.known_names()
    assert registry.get("Phase") is Phase


def test_discover_registers_custom_subclass(tmp_path, monkeypatch):
    """Discovery imports a real .py file and registers the Phase subclass it defines."""
    fake_dir = tmp_path / "fake_phases"
    fake_dir.mkdir()
    (fake_dir / "__init__.py").write_text("")
    (fake_dir / "custom.py").write_text("from ddev.ai.phases.base import Phase\nclass CustomPhase(Phase):\n    pass\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PhaseRegistry()
    _discover_and_register_phases(registry, phases_dir=fake_dir, import_prefix="fake_phases")

    assert "CustomPhase" in registry.known_names()
    assert issubclass(registry.get("CustomPhase"), Phase)


def test_discover_ignores_module_without_phase_subclass(tmp_path, monkeypatch):
    fake_dir = tmp_path / "no_phase_pkg"
    fake_dir.mkdir()
    (fake_dir / "__init__.py").write_text("")
    (fake_dir / "helpers.py").write_text("CONSTANT = 42\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PhaseRegistry()
    _discover_and_register_phases(registry, phases_dir=fake_dir, import_prefix="no_phase_pkg")

    assert registry.known_names() == []


def test_discover_does_not_register_imported_phase_class(tmp_path, monkeypatch):
    """A module that imports Phase but defines no subclass should not register Phase itself."""
    fake_dir = tmp_path / "importer_pkg"
    fake_dir.mkdir()
    (fake_dir / "__init__.py").write_text("")
    (fake_dir / "importer.py").write_text("from ddev.ai.phases.base import Phase\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PhaseRegistry()
    _discover_and_register_phases(registry, phases_dir=fake_dir, import_prefix="importer_pkg")

    assert "Phase" not in registry.known_names()


def test_discover_skips_underscore_prefixed_files():
    """After discovery, only non-underscore files are imported.
    __init__.py is underscore-prefixed and is skipped."""
    registry = PhaseRegistry()
    _discover_and_register_phases(registry)
    assert "Phase" in registry.known_names()


def test_discover_idempotent():
    registry = PhaseRegistry()
    _discover_and_register_phases(registry)
    first = registry.known_names()
    _discover_and_register_phases(registry)
    second = registry.known_names()
    assert first == second


def test_registry_get_unknown_raises():
    registry = PhaseRegistry()
    with pytest.raises(ValueError, match="Unknown phase type"):
        registry.get("NonexistentPhase")


def test_imported_class_not_registered():
    """A class imported into a phases module but defined elsewhere should not be registered."""
    registry = PhaseRegistry()
    _discover_and_register_phases(registry)
    # BaseMessage is imported in messages.py but defined in event_bus — it should NOT be registered
    assert "BaseMessage" not in registry.known_names()


def test_two_orchestrators_have_independent_registries(tmp_path):
    """Each PhaseOrchestrator owns its own registry; registering in one does not affect the other."""
    o1 = PhaseOrchestrator(
        flow_yaml_path=tmp_path / "flow.yaml",
        checkpoint_path=tmp_path / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    o2 = PhaseOrchestrator(
        flow_yaml_path=tmp_path / "flow.yaml",
        checkpoint_path=tmp_path / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )

    class ExclusivePhase(Phase):
        pass

    o1._phase_registry.register("ExclusivePhase", ExclusivePhase)
    assert "ExclusivePhase" in o1._phase_registry.known_names()
    assert "ExclusivePhase" not in o2._phase_registry.known_names()


def test_discover_does_not_mutate_global_state():
    """_discover_and_register_phases only touches the registry passed to it."""
    registry = PhaseRegistry()
    _discover_and_register_phases(registry)
    # No module-level / class-level container should have been touched.
    # Verify by checking there is no class-level _registry attribute on PhaseRegistry.
    assert not hasattr(PhaseRegistry, "_registry")


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_message_received
# ---------------------------------------------------------------------------


async def test_on_message_received_fatal_on_phase_failed():
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=Path("/fake/flow.yaml"),
        checkpoint_path=Path("/fake/checkpoints.yaml"),
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    msg = PhaseFailedMessage(id="f1", phase_id="p1", error="something broke")

    with pytest.raises(FatalProcessingError, match="Phase 'p1' failed"):
        await orchestrator.on_message_received(msg)


async def test_on_message_received_ignores_other_messages():
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=Path("/fake/flow.yaml"),
        checkpoint_path=Path("/fake/checkpoints.yaml"),
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
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
            type: Phase
            agent: writer
            tasks:
              - name: task_a
                prompt: task a
          b:
            type: Phase
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


async def test_on_initialize_registers_all_flow_phases(minimal_flow):
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=minimal_flow / "flow.yaml",
        checkpoint_path=minimal_flow / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    phase_names = {p.name for p in processors}
    assert phase_names == {"a", "b"}


async def test_on_initialize_wires_dependencies(minimal_flow):
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=minimal_flow / "flow.yaml",
        checkpoint_path=minimal_flow / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    phases_by_name = {p.name: p for p in processors}
    assert phases_by_name["a"]._dependencies == set()
    assert phases_by_name["b"]._dependencies == {"a"}


async def test_on_initialize_submits_initial_phase_trigger(minimal_flow):
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=minimal_flow / "flow.yaml",
        checkpoint_path=minimal_flow / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    await orchestrator.on_initialize()

    assert not orchestrator._queue.empty()
    msg = orchestrator._queue.get_nowait()
    assert isinstance(msg, PhaseTrigger)
    assert msg.phase_id is None


async def test_on_initialize_unknown_phase_type_raises_flow_config_error(tmp_path):
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
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=tmp_path / "flow.yaml",
        checkpoint_path=tmp_path / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    with pytest.raises(FlowConfigError, match="Unknown phase type"):
        await orchestrator.on_initialize()


async def test_on_initialize_missing_agent_raises(tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          a:
            type: Phase
            agent: nonexistent_agent
            tasks:
              - name: task_a
                prompt: task a
        flow:
          - phase: a
        """)
    )
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=tmp_path / "flow.yaml",
        checkpoint_path=tmp_path / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    with pytest.raises(FlowConfigError):
        await orchestrator.on_initialize()


# ---------------------------------------------------------------------------
# PhaseOrchestrator.on_initialize — orphan-phase validation
# ---------------------------------------------------------------------------


async def test_orphan_phase_with_unknown_type_does_not_block_init(tmp_path):
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
            type: Phase
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
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=tmp_path / "flow.yaml",
        checkpoint_path=tmp_path / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    await orchestrator.on_initialize()

    processors = orchestrator._subscribers.get(PhaseTrigger, [])
    assert {p.name for p in processors} == {"real"}


async def test_phase_in_flow_with_unknown_type_raises(tmp_path):
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
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=tmp_path / "flow.yaml",
        checkpoint_path=tmp_path / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    with pytest.raises(FlowConfigError, match="Unknown phase type"):
        await orchestrator.on_initialize()


async def test_orphan_phase_logs_warning(tmp_path, caplog):
    """An orphan phase must emit a warning containing its phase id."""
    import logging

    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "writer.md").write_text("system prompt")
    (tmp_path / "flow.yaml").write_text(
        dedent("""\
        agents:
          writer:
            tools: []
        phases:
          real:
            type: Phase
            agent: writer
            tasks:
              - name: t1
                prompt: do it
          orphan:
            type: Phase
            agent: writer
            tasks:
              - name: t2
                prompt: ignored
        flow:
          - phase: real
        """)
    )
    orchestrator = PhaseOrchestrator(
        flow_yaml_path=tmp_path / "flow.yaml",
        checkpoint_path=tmp_path / "checkpoints.yaml",
        runtime_variables={},
        anthropic_client=MagicMock(),
    )
    with caplog.at_level(logging.WARNING):
        await orchestrator.on_initialize()

    assert any("orphan" in record.message for record in caplog.records)
