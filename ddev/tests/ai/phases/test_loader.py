# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from pathlib import Path

import pytest

from ddev.ai.config.errors import FlowConfigError
from ddev.ai.config.models import AgentConfig, FlowEntry, PhaseConfig, ResolvedFlow
from ddev.ai.phases.agentic_phase import AgenticPhase
from ddev.ai.phases.loader import PhaseLoader, _import_prefix_from_path


def empty_flow() -> ResolvedFlow:
    return ResolvedFlow(name="f", agents={}, phases={}, flow=[], variables={})


def flow_with_phase(phase_id: str, class_: str, agent: str | None = None) -> ResolvedFlow:
    agents = {}
    if agent is not None:
        agents[agent] = AgentConfig(name=agent)
    phase = PhaseConfig(name=phase_id, class_=class_, agent=agent)
    return ResolvedFlow(
        name="f",
        agents=agents,
        phases={phase_id: phase},
        flow=[FlowEntry(phase=phase_id)],
        variables={},
    )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def test_load_discovers_agentic_phase():
    loader = PhaseLoader()
    registry = loader.load(empty_flow())
    assert "AgenticPhase" in registry.known_names()
    assert registry.get("AgenticPhase").__name__ == "AgenticPhase"


def test_load_discovers_custom_class_in_user_phases_subdir(tmp_path, monkeypatch):
    user_dir = tmp_path / "myflows"
    phases_dir = user_dir / "phases"
    phases_dir.mkdir(parents=True)
    (phases_dir / "__init__.py").write_text("")
    (phases_dir / "custom.py").write_text(
        "from ddev.ai.phases.agentic_phase import AgenticPhase\nclass MyPhase(AgenticPhase):\n    pass\n"
    )
    monkeypatch.syspath_prepend(str(user_dir))

    loader = PhaseLoader(user_dirs=[user_dir])
    registry = loader.load(empty_flow())
    assert "MyPhase" in registry.known_names()
    assert issubclass(registry.get("MyPhase"), AgenticPhase)


def test_load_skips_user_dir_with_no_phases_subdir(tmp_path):
    loader = PhaseLoader(user_dirs=[tmp_path])
    registry = loader.load(empty_flow())
    # Only core phases — no extra classes from tmp_path
    assert "AgenticPhase" in registry.known_names()


def test_duplicate_dirs_not_processed_twice(tmp_path):
    user_dir = tmp_path / "myflows"
    phases_dir = user_dir / "phases"
    phases_dir.mkdir(parents=True)
    loader = PhaseLoader(user_dirs=[user_dir, user_dir])
    registry = loader.load(empty_flow())
    names = registry.known_names()
    assert len(names) == len(set(names))


def test_path_not_on_sys_path_warns_and_skips(tmp_path, caplog):
    phases_dir = tmp_path / "phases"
    phases_dir.mkdir()
    loader = PhaseLoader(user_dirs=[tmp_path])
    with caplog.at_level(logging.WARNING):
        registry = loader.load(empty_flow())
    assert any("sys.path" in r.message for r in caplog.records)


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
    phase = PhaseConfig(name="p", class_="AgenticPhase", agent="writer", tasks=[])
    resolved = ResolvedFlow(name="f", agents=agents, phases={"p": phase}, flow=[FlowEntry(phase="p")], variables={})
    with pytest.raises(FlowConfigError, match="at least one task"):
        loader.load(resolved)



# ---------------------------------------------------------------------------
# Registry independence
# ---------------------------------------------------------------------------


def test_two_load_calls_return_independent_registries():
    loader = PhaseLoader()
    r1 = loader.load(empty_flow())
    r2 = loader.load(empty_flow())
    assert r1 is not r2


# ---------------------------------------------------------------------------
# _import_prefix_from_path
# ---------------------------------------------------------------------------


def test_import_prefix_from_path_not_on_sys_path(tmp_path):
    path = tmp_path / "nowhere"
    path.mkdir()
    with pytest.raises(RuntimeError, match="Could not derive import prefix"):
        _import_prefix_from_path(path)
