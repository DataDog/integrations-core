# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for screen navigation and screen skeletons: FlowScreen, ExecutionScreen."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Navigation: FlowCard → FlowScreen
# ---------------------------------------------------------------------------


async def test_enter_on_flow_card_pushes_flow_screen(make_flow, make_togo_app):
    """Pressing Enter when the app starts opens the first flow."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    alpha_flow = make_flow("Alpha Flow", n_phases=3)
    app = make_togo_app([make_flow("Beta Flow", n_phases=1), alpha_flow])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        await pilot.press("enter")
        await pilot.pause()
        flow_screen = pilot.app.screen
        assert isinstance(flow_screen, FlowScreen)
        assert flow_screen.flow is alpha_flow


async def test_enter_on_opened_flow_pushes_launch_modal(make_flow, make_togo_app):
    """Pressing Enter immediately after opening a flow opens its launch modal."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    app = make_togo_app([make_flow("Alpha Flow", n_phases=3)])
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(pilot.app.screen, FlowScreen)

        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(pilot.app.screen, LaunchModal)


async def test_flow_screen_receives_correct_flow(make_flow, make_togo_app):
    """FlowScreen is pushed with the ResolvedFlow matching the selected card."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard

    app = make_togo_app([make_flow("Alpha Flow", n_phases=3), make_flow("Beta Flow", n_phases=1)])
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        cards = list(pilot.app.screen.query(FlowCard))
        first_card = cards[0]
        expected_flow = first_card.flow
        first_card.focus()
        await pilot.press("enter")
        await pilot.pause()
        flow_screen: FlowScreen = pilot.app.screen  # type: ignore[assignment]
        assert flow_screen.flow is expected_flow


# ---------------------------------------------------------------------------
# FlowScreen skeleton
# ---------------------------------------------------------------------------


async def test_flow_screen_mounts_on_shell(make_flow, make_togo_app):
    """FlowScreen can be pushed onto the app and mounts without error."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = make_flow("Push Test", n_phases=2)
    app = make_togo_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        assert isinstance(pilot.app.screen, FlowScreen)


async def test_flow_screen_carries_flow_config(make_flow):
    """FlowScreen exposes the ResolvedFlow it was constructed with."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

    flow = make_flow("Config Carrier", n_phases=2)
    screen = FlowScreen(flow)
    assert screen.flow is flow


# ---------------------------------------------------------------------------
# ExecutionScreen skeleton
# ---------------------------------------------------------------------------


async def test_execution_screen_is_togo_screen():
    """ExecutionScreen extends TogoScreen."""
    from ddev.cli.meta.ai.tui.screens.base import TogoScreen
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    assert issubclass(ExecutionScreen, TogoScreen)


async def test_execution_screen_accepts_flow_and_defaults(make_flow):
    """ExecutionScreen.__init__ accepts flow with runtime_variables=None, resume=False."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = make_flow("Exec", n_phases=2)
    screen = ExecutionScreen(flow)
    assert screen.flow is flow
    assert screen.runtime_variables is None
    assert screen.resume is False


async def test_execution_screen_accepts_runtime_variables(make_flow):
    """ExecutionScreen stores runtime_variables when supplied."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = make_flow("Exec Vars", n_phases=1)
    rv = {"target": "World"}
    screen = ExecutionScreen(flow, runtime_variables=rv)
    assert screen.runtime_variables == rv


async def test_execution_screen_accepts_resume_flag(make_flow):
    """ExecutionScreen stores resume=True when supplied."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = make_flow("Exec Resume", n_phases=1)
    screen = ExecutionScreen(flow, resume=True)
    assert screen.resume is True


async def test_execution_screen_mounts_with_placeholder_regions(make_flow, make_togo_app):
    """ExecutionScreen mounts with a full graph region."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PipelineGraph

    flow = make_flow("Exec Mount", n_phases=2)
    app = make_togo_app()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        await pilot.app.push_screen(ExecutionScreen(flow))
        await pilot.pause()
        assert isinstance(pilot.app.screen, ExecutionScreen)
        pilot.app.screen.query_one("#pipeline", PipelineGraph)
