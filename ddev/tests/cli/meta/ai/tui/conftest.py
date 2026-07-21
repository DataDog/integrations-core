# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config.models import (
    AgentConfig,
    ConfigStatus,
    FlowConfig,
    FlowEntry,
    FlowInput,
    FlowResult,
    InputType,
    PhaseConfig,
    ResolvedFlow,
    TaskConfig,
)
from ddev.ai.phases.registry import PhaseRegistry
from ddev.cli.meta.ai.tui.app import TogoApp
from ddev.cli.meta.ai.tui.theme import togo_theme

LARGE_TERMINAL = (120, 50)
STATUS_VARIABLE_KEYS = ("status-running", "status-pending", "status-done", "status-failed")


def make_test_ddev_app(api_key: str | None = None, repo_path: Path | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(ai=SimpleNamespace(anthropic_api_key=api_key, flow_dirs=[])),
        repo=SimpleNamespace(path=str(repo_path or Path.cwd())),
    )


class StaticConfigurationEngine:
    def __init__(self, flows: list[ResolvedFlow], results: list[FlowResult] | None = None) -> None:
        self.flows = (
            {result.name: result for result in results}
            if results is not None
            else {flow.name: FlowResult(flow.name, ConfigStatus.OK, resolved=flow) for flow in flows}
        )

    def get_flow(self, name: str) -> ResolvedFlow:
        result = self.flows[name]
        assert result.resolved is not None
        return result.resolved


class TogoModalTestApp(App):
    CSS_PATH = TogoApp.CSS_PATH

    def get_theme_variable_defaults(self) -> dict[str, str]:
        return {key: togo_theme.variables[key] for key in STATUS_VARIABLE_KEYS}


class LaunchModalTestApp(TogoModalTestApp):
    """Minimal app that pushes LaunchModal immediately on mount."""

    def __init__(self, flow: ResolvedFlow, prd_path: Path) -> None:
        super().__init__()
        self.flow = flow
        self.prd_path = prd_path
        self.dismiss_result: Any = "NOT_SET"

    def compose(self) -> ComposeResult:
        yield from []

    def on_mount(self) -> None:
        from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

        self.register_theme(togo_theme)
        self.theme = "togo"

        def on_dismiss(result: Any) -> None:
            self.dismiss_result = result

        self.push_screen(LaunchModal(self.flow), on_dismiss)
        self.call_after_refresh(self._populate_prd)

    def _populate_prd(self) -> None:
        self.screen.query_one("#input-prd", Input).value = str(self.prd_path)


@pytest.fixture
def large_terminal() -> tuple[int, int]:
    """A viewport large enough for modal button click tests."""
    return LARGE_TERMINAL


@pytest.fixture
def ddev_app() -> SimpleNamespace:
    return make_test_ddev_app()


@pytest.fixture
def make_flow() -> Callable[..., ResolvedFlow]:
    def factory(
        name: str = "Test Flow",
        n_phases: int = 2,
        *,
        inputs: list[FlowInput] | None = None,
        agents: dict[str, AgentConfig] | None = None,
    ) -> ResolvedFlow:
        flow_agents = agents or {"agent_a": AgentConfig.model_construct(provider="anthropic", tools=[])}
        agent_name = next(iter(flow_agents))
        phases = {
            f"phase_{i}": PhaseConfig(
                name=f"phase_{i}",
                agent=agent_name,
                tasks=[TaskConfig(name=f"task_{i}", prompt="do something")],
            )
            for i in range(n_phases)
        }
        flow = [FlowEntry(phase=f"phase_{i}") for i in range(n_phases)]
        return ResolvedFlow(
            name=name,
            description=f"Description for {name}",
            inputs=FlowConfig(name="test", inputs=inputs or [], flow=[]).inputs,
            agents=flow_agents,
            phases=phases,
            flow=flow,
            variables={},
        )

    return factory


@pytest.fixture
def make_flow_with_tools() -> Callable[..., ResolvedFlow]:
    def factory(name: str = "Tool Flow") -> ResolvedFlow:
        agents = {
            "analyst": AgentConfig.model_construct(provider="anthropic", model="claude-3-sonnet", tools=["read_file"])
        }
        phases = {
            "analyse": PhaseConfig(
                name="analyse",
                agent="analyst",
                tasks=[TaskConfig(name="read_task", prompt="analyse something")],
            )
        }
        return ResolvedFlow(
            name=name,
            description="Tool flow",
            inputs=FlowConfig(name="test", flow=[]).inputs,
            agents=agents,
            phases=phases,
            flow=[FlowEntry(phase="analyse")],
            variables={},
        )

    return factory


@pytest.fixture
def all_flow_inputs() -> list[FlowInput]:
    return [
        FlowInput(name="my_string", label="My String", input_type=InputType.STRING, default="hello", required=True),
        FlowInput(name="my_number", label="My Number", input_type=InputType.NUMBER, default=42, required=True),
        FlowInput(name="my_bool", label="My Bool", input_type=InputType.BOOLEAN, default=True, required=False),
        FlowInput(name="my_path", label="My Path", input_type=InputType.PATH, default="/tmp", required=False),
    ]


@pytest.fixture
def make_togo_app(make_flow: Callable[..., ResolvedFlow], ddev_app: SimpleNamespace) -> Callable[..., TogoApp]:
    def factory(
        flows: list[ResolvedFlow] | None = None,
        *,
        results: list[FlowResult] | None = None,
    ) -> TogoApp:
        return TogoApp(
            engine=StaticConfigurationEngine([make_flow()] if flows is None else flows, results),
            phase_registry=PhaseRegistry(),
            provider_registry=AgentProviderRegistry(),
            ddev_app=ddev_app,
        )

    return factory


@pytest.fixture
def make_launch_modal_app(make_flow: Callable[..., ResolvedFlow], tmp_path: Path) -> Callable[..., LaunchModalTestApp]:
    prd_path = tmp_path / "prd.md"
    prd_path.write_text("Required product behavior.\n", encoding="utf-8")

    def factory(inputs: list[FlowInput]) -> LaunchModalTestApp:
        return LaunchModalTestApp(make_flow(name="Test Flow", n_phases=1, inputs=inputs), prd_path)

    return factory
