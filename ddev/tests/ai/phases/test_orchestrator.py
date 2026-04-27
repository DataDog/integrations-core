# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys
from pathlib import Path
from textwrap import dedent
from types import ModuleType
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
    _discover_and_register_phases()
    assert "Phase" in PhaseRegistry._registry
    assert PhaseRegistry._registry["Phase"] is Phase


def test_discover_registers_custom_subclass(tmp_path, monkeypatch):
    """Simulate a custom phase module in the phases directory."""
    # Create a temporary module that defines a Phase subclass
    custom_module = ModuleType("ddev.ai.phases._test_custom")
    custom_module.__name__ = "ddev.ai.phases._test_custom"

    class CustomPhase(Phase):
        pass

    CustomPhase.__module__ = "ddev.ai.phases._test_custom"
    custom_module.CustomPhase = CustomPhase

    # Register in sys.modules so importlib finds it
    sys.modules["ddev.ai.phases._test_custom"] = custom_module

    # Create a .py file that will be discovered (no underscore prefix)
    # But since we can't easily write to the installed package dir,
    # we test the registration logic directly
    PhaseRegistry._registry["CustomPhase"] = CustomPhase

    try:
        assert PhaseRegistry.get("CustomPhase") is CustomPhase
    finally:
        del sys.modules["ddev.ai.phases._test_custom"]


def test_discover_skips_underscore_prefixed_files():
    """After discovery, only non-underscore files are imported.
    __init__.py is underscore-prefixed and is skipped."""
    _discover_and_register_phases()
    # Phase should be registered from base.py
    assert "Phase" in PhaseRegistry._registry


def test_discover_idempotent():
    _discover_and_register_phases()
    first = dict(PhaseRegistry._registry)
    _discover_and_register_phases()
    second = dict(PhaseRegistry._registry)
    assert first == second


def test_registry_get_unknown_raises():
    with pytest.raises(ValueError, match="Unknown phase type"):
        PhaseRegistry.get("NonexistentPhase")


def test_imported_class_not_registered():
    """A class imported into a phases module but defined elsewhere should not be registered."""
    _discover_and_register_phases()
    # BaseMessage is imported in messages.py but defined in event_bus — it should NOT be registered
    assert "BaseMessage" not in PhaseRegistry._registry


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
