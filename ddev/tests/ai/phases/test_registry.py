# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest

from ddev.ai.phases.agentic_phase import AgenticPhase
from ddev.ai.phases.registry import PhaseRegistry, discover_and_register_phases

FRAMEWORK_PHASES_DIR = Path(__file__).resolve().parents[3] / "src" / "ddev" / "ai" / "phases"
FRAMEWORK_IMPORT_PREFIX = "ddev.ai.phases"


def test_discover_registers_agentic_phase():
    registry = PhaseRegistry()
    discover_and_register_phases(registry, FRAMEWORK_PHASES_DIR, FRAMEWORK_IMPORT_PREFIX)
    assert "AgenticPhase" in registry.known_names()
    assert registry.get("AgenticPhase") is AgenticPhase


def test_discover_registers_custom_subclass(tmp_path, monkeypatch):
    """Discovery imports a real .py file and registers the Phase subclass it defines."""
    fake_dir = tmp_path / "fake_phases"
    fake_dir.mkdir()
    (fake_dir / "__init__.py").write_text("")
    (fake_dir / "custom.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\nclass CustomPhase(AgenticPhase):\n    pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PhaseRegistry()
    discover_and_register_phases(registry, phases_dir=fake_dir, import_prefix="fake_phases")

    assert "CustomPhase" in registry.known_names()
    assert issubclass(registry.get("CustomPhase"), AgenticPhase)


def test_discover_ignores_module_without_phase_subclass(tmp_path, monkeypatch):
    fake_dir = tmp_path / "no_phase_pkg"
    fake_dir.mkdir()
    (fake_dir / "__init__.py").write_text("")
    (fake_dir / "helpers.py").write_text("CONSTANT = 42\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PhaseRegistry()
    discover_and_register_phases(registry, phases_dir=fake_dir, import_prefix="no_phase_pkg")

    assert registry.known_names() == []


def test_discover_does_not_register_imported_phase_class(tmp_path, monkeypatch):
    """A module that imports Phase but defines no subclass should not register Phase itself."""
    fake_dir = tmp_path / "importer_pkg"
    fake_dir.mkdir()
    (fake_dir / "__init__.py").write_text("")
    (fake_dir / "importer.py").write_text("from ddev.ai.phases.agentic_phase import AgenticPhase\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PhaseRegistry()
    discover_and_register_phases(registry, phases_dir=fake_dir, import_prefix="importer_pkg")

    assert "AgenticPhase" not in registry.known_names()


def test_discover_skips_underscore_prefixed_files(tmp_path, monkeypatch):
    """Classes defined in underscore-prefixed files (e.g. _private.py) are never registered."""
    fake_dir = tmp_path / "underscore_pkg"
    fake_dir.mkdir()
    (fake_dir / "__init__.py").write_text("")
    (fake_dir / "_private.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\nclass PrivatePhase(AgenticPhase):\n    pass\n"
    )
    (fake_dir / "public.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\nclass PublicPhase(AgenticPhase):\n    pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    registry = PhaseRegistry()
    discover_and_register_phases(registry, phases_dir=fake_dir, import_prefix="underscore_pkg")

    assert "PrivatePhase" not in registry.known_names()
    assert "PublicPhase" in registry.known_names()


def test_discover_idempotent():
    registry = PhaseRegistry()
    discover_and_register_phases(registry, FRAMEWORK_PHASES_DIR, FRAMEWORK_IMPORT_PREFIX)
    first = registry.known_names()
    discover_and_register_phases(registry, FRAMEWORK_PHASES_DIR, FRAMEWORK_IMPORT_PREFIX)
    second = registry.known_names()
    assert first == second


def test_registry_get_unknown_raises():
    registry = PhaseRegistry()
    with pytest.raises(ValueError, match="Unknown phase type"):
        registry.get("NonexistentPhase")


def test_imported_class_not_registered():
    """A class imported into a phases module but defined elsewhere should not be registered."""
    registry = PhaseRegistry()
    discover_and_register_phases(registry, FRAMEWORK_PHASES_DIR, FRAMEWORK_IMPORT_PREFIX)
    # BaseMessage is imported in messages.py but defined in event_bus — it should NOT be registered
    assert "BaseMessage" not in registry.known_names()


def test_discover_does_not_mutate_global_state():
    """_discover_and_register_phases only touches the registry passed to it."""
    registry = PhaseRegistry()
    discover_and_register_phases(registry, FRAMEWORK_PHASES_DIR, FRAMEWORK_IMPORT_PREFIX)
    # No module-level / class-level container should have been touched.
    # Verify by checking there is no class-level _registry attribute on PhaseRegistry.
    assert not hasattr(PhaseRegistry, "_registry")
