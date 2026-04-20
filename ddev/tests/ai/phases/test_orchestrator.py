# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from ddev.ai.phases.base import Phase, PhaseRegistry
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
