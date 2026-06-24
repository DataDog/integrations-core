# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import sys
from pathlib import Path

import pytest

from ddev.ai.config.errors import FlowConfigError
from ddev.ai.config.models import AgentConfig, FlowEntry, PhaseConfig, ResolvedFlow
from ddev.ai.phases.agentic_phase import AgenticPhase
from ddev.ai.phases.loader import (
    ROOT_PACKAGE,
    PhaseLoader,
    normalize_flow_name,
)


def empty_flow(name: str = "my_flow") -> ResolvedFlow:
    return ResolvedFlow(name=name, agents={}, phases={}, flow=[], variables={})


def flow_with_phase(phase_id: str, class_: str, agent: str | None = None, flow_name: str = "my_flow") -> ResolvedFlow:
    agents = {}
    if agent is not None:
        agents[agent] = AgentConfig(name=agent)
    phase = PhaseConfig(name=phase_id, class_=class_, agent=agent)
    return ResolvedFlow(
        name=flow_name,
        agents=agents,
        phases={phase_id: phase},
        flow=[FlowEntry(phase=phase_id)],
        variables={},
    )


# ---------------------------------------------------------------------------
# normalize_flow_name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("my-flow", "my_flow"),
        ("My Flow", "my_flow"),
        ("openmetrics", "openmetrics"),
        ("my--flow", "my_flow"),
        ("123flow", "flow_123flow"),
        ("flow123", "flow123"),
        ("a b c", "a_b_c"),
        ("---", "flow"),
    ],
)
def test_normalize_flow_name(name, expected):
    assert normalize_flow_name(name) == expected


# ---------------------------------------------------------------------------
# Core phase discovery
# ---------------------------------------------------------------------------


def test_load_discovers_agentic_phase():
    loader = PhaseLoader()
    registry = loader.load(empty_flow())
    assert "AgenticPhase" in registry.known_names()
    assert registry.get("AgenticPhase").__name__ == "AgenticPhase"


def test_two_load_calls_return_independent_registries():
    loader = PhaseLoader()
    r1 = loader.load(empty_flow())
    r2 = loader.load(empty_flow())
    assert r1 is not r2


# ---------------------------------------------------------------------------
# User phase discovery (synthetic packages)
# ---------------------------------------------------------------------------


def _write_phase_class(path: Path, class_name: str, base: str = "AgenticPhase") -> None:
    path.write_text(
        f"from ddev.ai.phases.agentic_phase import AgenticPhase\n"
        f"class {class_name}({base}):\n"
        f"    pass\n"
    )


def test_load_discovers_phase_in_flow_subdir(tmp_path):
    phases_dir = tmp_path / "my_flow" / "phases"
    phases_dir.mkdir(parents=True)
    _write_phase_class(phases_dir / "custom.py", "MyPhase")

    loader = PhaseLoader(user_dirs=[tmp_path])
    registry = loader.load(empty_flow("my_flow"))
    assert "MyPhase" in registry.known_names()
    assert issubclass(registry.get("MyPhase"), AgenticPhase)


def test_load_discovers_phase_in_shared_subdir(tmp_path):
    phases_dir = tmp_path / "shared" / "phases"
    phases_dir.mkdir(parents=True)
    _write_phase_class(phases_dir / "shared_phase.py", "SharedPhase")

    loader = PhaseLoader(user_dirs=[tmp_path])
    registry = loader.load(empty_flow("my_flow"))
    assert "SharedPhase" in registry.known_names()


def test_load_skips_user_dir_with_no_matching_phases_subdir(tmp_path):
    loader = PhaseLoader(user_dirs=[tmp_path])
    registry = loader.load(empty_flow("my_flow"))
    # Only core phases — tmp_path has no flow/phases or shared/phases
    assert "AgenticPhase" in registry.known_names()
    # No extra unknown classes
    assert all("AgenticPhase" in name or "Phase" in name for name in registry.known_names())


def test_load_skips_private_files(tmp_path):
    phases_dir = tmp_path / "my_flow" / "phases"
    phases_dir.mkdir(parents=True)
    (phases_dir / "_helpers.py").write_text("x = 1\n")
    (phases_dir / "custom.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\nclass MyPhase(AgenticPhase): pass\n"
    )

    loader = PhaseLoader(user_dirs=[tmp_path])
    registry = loader.load(empty_flow("my_flow"))
    assert "MyPhase" in registry.known_names()
    # _helpers is not a phase class and its contents should not appear
    assert "_helpers" not in registry.known_names()


def test_load_skips_classes_defined_elsewhere(tmp_path):
    """Classes imported into a phase file should not be re-registered."""
    phases_dir = tmp_path / "my_flow" / "phases"
    phases_dir.mkdir(parents=True)
    (phases_dir / "custom.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\n"
        "class MyPhase(AgenticPhase): pass\n"
    )

    loader = PhaseLoader(user_dirs=[tmp_path])
    registry = loader.load(empty_flow("my_flow"))
    # AgenticPhase is imported, not defined in custom.py — must not be duplicated
    names = registry.known_names()
    assert names.count("AgenticPhase") == 1



def test_load_relative_imports_work(tmp_path):
    """Phase files can import siblings using relative imports."""
    phases_dir = tmp_path / "my_flow" / "phases"
    phases_dir.mkdir(parents=True)
    (phases_dir / "_helpers.py").write_text("HELPER = 'ok'\n")
    (phases_dir / "custom.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\n"
        "from ._helpers import HELPER\n"
        "class RelativePhase(AgenticPhase):\n"
        "    helper = HELPER\n"
    )

    loader = PhaseLoader(user_dirs=[tmp_path])
    registry = loader.load(empty_flow("my_flow"))
    assert "RelativePhase" in registry.known_names()
    assert registry.get("RelativePhase").helper == "ok"


def test_load_two_flows_same_filename_do_not_conflict(tmp_path):
    """Two flows can each have a phases/custom.py with a different class name."""
    for flow_name in ("flow_a", "flow_b"):
        phases_dir = tmp_path / flow_name / "phases"
        phases_dir.mkdir(parents=True)
        class_name = f"Phase_{flow_name.upper()}"
        _write_phase_class(phases_dir / "custom.py", class_name)

    loader_a = PhaseLoader(user_dirs=[tmp_path])
    loader_b = PhaseLoader(user_dirs=[tmp_path])

    registry_a = loader_a.load(empty_flow("flow_a"))
    registry_b = loader_b.load(empty_flow("flow_b"))

    assert "Phase_FLOW_A" in registry_a.known_names()
    assert "Phase_FLOW_B" in registry_b.known_names()


def test_load_uses_synthetic_package_namespace(tmp_path):
    """Imported modules must live under ROOT_PACKAGE, not under 'phases'."""
    phases_dir = tmp_path / "my_flow" / "phases"
    phases_dir.mkdir(parents=True)
    _write_phase_class(phases_dir / "custom.py", "SyntheticPhase")

    loader = PhaseLoader(user_dirs=[tmp_path])
    loader.load(empty_flow("my_flow"))

    # Module lives under ROOT_PACKAGE with a path-derived suffix, not bare 'phases'
    matching = [k for k in sys.modules if ".phases.custom" in k and k.startswith(ROOT_PACKAGE)]
    assert matching, f"No synthetic module for custom.py found under {ROOT_PACKAGE}"


def test_load_invalid_filename_raises(tmp_path):
    phases_dir = tmp_path / "my_flow" / "phases"
    phases_dir.mkdir(parents=True)
    (phases_dir / "my-phase.py").write_text("x = 1\n")

    loader = PhaseLoader(user_dirs=[tmp_path])
    with pytest.raises(FlowConfigError, match="Invalid phase module filename"):
        loader.load(empty_flow("my_flow"))


def test_load_duplicate_phase_type_raises(tmp_path):
    phases_dir = tmp_path / "my_flow" / "phases"
    phases_dir.mkdir(parents=True)
    (phases_dir / "a.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\n"
        "class DupPhase(AgenticPhase): pass\n"
    )
    (phases_dir / "b.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\n"
        "class DupPhase(AgenticPhase): pass\n"
    )

    loader = PhaseLoader(user_dirs=[tmp_path])
    with pytest.raises(FlowConfigError, match="Duplicate phase type"):
        loader.load(empty_flow("my_flow"))



def test_load_import_error_raises_flow_config_error(tmp_path):
    phases_dir = tmp_path / "my_flow" / "phases"
    phases_dir.mkdir(parents=True)
    (phases_dir / "broken.py").write_text("raise ImportError('intentional')\n")

    loader = PhaseLoader(user_dirs=[tmp_path])
    with pytest.raises(FlowConfigError, match="broken.py"):
        loader.load(empty_flow("my_flow"))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_load_raises_on_unknown_class_in_flow():
    loader = PhaseLoader()
    resolved = flow_with_phase("p", "BogusClass")
    with pytest.raises(FlowConfigError, match="BogusClass"):
        loader.load(resolved)


def test_load_calls_validate_config_for_flow_phases():
    """AgenticPhase.validate_config rejects empty tasks list."""
    loader = PhaseLoader()
    agents = {"writer": AgentConfig(name="writer")}
    phase = PhaseConfig(name="p", agent="writer", tasks=[])
    resolved = ResolvedFlow(name="my_flow", agents=agents, phases={"p": phase}, flow=[FlowEntry(phase="p")], variables={})
    with pytest.raises(FlowConfigError, match="at least one task"):
        loader.load(resolved)


