# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for ExecutionScreen live wiring and fake orchestrator (test-internal only)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Input

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config.models import (
    AgentConfig,
    FlowConfig,
    FlowEntry,
    FlowInput,
    InputType,
    PhaseConfig,
    ResolvedFlow,
    TaskConfig,
)
from ddev.ai.phases import notices as phase_notices
from ddev.ai.phases.registry import PhaseRegistry
from ddev.ai.react import notices
from ddev.ai.run_events import RunEvents
from ddev.ai.runtime.notices import RunErrored as RunErroredNotice
from ddev.cli.meta.ai.tui.app import TogoApp
from ddev.cli.meta.ai.tui.messages import NoticeMessage
from ddev.cli.meta.ai.tui.status import RunStatus

from .conftest import StaticConfigurationEngine, export_screenshot_text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEMO_PHASES = [
    ("phase_1", ["task_one"]),
    ("phase_2", ["task_two"]),
]


def _make_flow(
    name: str = "Test Flow",
    phases: list[tuple[str, list[str]]] | None = None,
) -> ResolvedFlow:
    """Build a ResolvedFlow matching the given (phase_id, task_names) list."""
    if phases is None:
        phases = DEMO_PHASES
    agents = {"agent_a": AgentConfig.model_construct(provider="anthropic", model="claude-3-sonnet", tools=[])}
    phase_configs = {
        phase_id: PhaseConfig(
            name=phase_id,
            agent="agent_a",
            tasks=[TaskConfig(name=task_name, prompt="do it") for task_name in task_names],
        )
        for phase_id, task_names in phases
    }
    flow_entries = [FlowEntry(phase=phase_id) for phase_id, _ in phases]
    return ResolvedFlow(
        name=name,
        description="A test flow",
        inputs=FlowConfig(
            name="test",
            flow=[],
            inputs=[
                FlowInput(
                    name="integration",
                    label="Integration name",
                    input_type=InputType.STRING,
                    default="My Integration",
                )
            ],
        ).inputs,
        agents=agents,
        phases=phase_configs,
        flow=flow_entries,
        variables={},
    )


def _make_dag_flow() -> ResolvedFlow:
    """Build a flow with branching and fan-in dependencies."""
    agents = {"agent_a": AgentConfig.model_construct(provider="anthropic", model="claude-3-sonnet", tools=[])}
    phase_ids = ["research", "write_readme", "write_script", "write_tests", "final_review"]
    phase_configs = {
        phase_id: PhaseConfig(
            name=phase_id,
            agent="agent_a",
            tasks=[TaskConfig(name=f"{phase_id}_task", prompt="do it")],
        )
        for phase_id in phase_ids
    }
    return ResolvedFlow(
        name="DAG Flow",
        description="A dependency graph test flow",
        agents=agents,
        phases=phase_configs,
        flow=[
            FlowEntry(phase="research"),
            FlowEntry(phase="write_readme", dependencies=["research"]),
            FlowEntry(phase="write_script", dependencies=["research"]),
            FlowEntry(phase="write_tests", dependencies=["write_script"]),
            FlowEntry(phase="final_review", dependencies=["write_readme", "write_script", "write_tests"]),
        ],
        variables={},
    )


def _demo_dir() -> Path:
    import ddev.ai

    return Path(ddev.ai.__file__).parent / "flows" / "demo"


# ---------------------------------------------------------------------------
# Test-only fake orchestrator — scripted, no API key, no real agents.
# This is a test double that lives ONLY in the test module.
# The shipped tui/ package contains no fake/demo orchestrators.
# ---------------------------------------------------------------------------


def _make_token_usage() -> Any:
    from ddev.ai.agent.types import TokenUsage

    return TokenUsage(
        input_tokens=100,
        output_tokens=50,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )


def _make_agent_response(text: str) -> Any:
    from ddev.ai.agent.types import AgentResponse, StopReason, WebActivity

    return AgentResponse(
        stop_reason=StopReason.END_TURN,
        text=text,
        tool_calls=[],
        usage=_make_token_usage(),
        web_activity=WebActivity(),
    )


def _make_react_result(response: Any) -> Any:
    from ddev.ai.react.types import ReActResult

    return ReActResult(
        final_response=response,
        iterations=2,
        total_input_tokens=200,
        total_output_tokens=100,
        context_usage=None,
    )


class _FakeOrchestrator:
    """Scripted fake orchestrator for tests — no API key, no real agents.

    Publishes run notices without any API key or real agents.
    Tests inject it into ``ExecutionScreen`` via the ``orchestrator_builder``
    parameter to verify pipeline, task, and output rendering.
    """

    def __init__(
        self,
        events: RunEvents,
        phases: list[tuple[str, list[str]]],
        *,
        fail_on_phase: str | None = None,
    ) -> None:
        self._events = events
        self._phases = phases
        self._fail_on_phase = fail_on_phase
        self.failed_phase: str | None = None

    async def run_async(self) -> None:
        """Send the scripted event sequence."""
        for phase_id, task_names in self._phases:
            await self._run_phase(phase_id, task_names)

    async def _run_phase(self, phase_id: str, task_names: list[str]) -> None:
        from ddev.ai.agent.scope import AgentRole, AgentScope
        from ddev.ai.agent.types import ToolCall
        from ddev.ai.react.process import TOOL_RESULTS_SENTINEL
        from ddev.ai.tools.core.types import ToolResult

        scope = AgentScope(owner_id=phase_id, role=AgentRole.PHASE, phase_id=phase_id)
        await self._events.notify(phase_notices.PhaseStarted(phase_id))
        await self._events.notify(notices.AgentStarted(scope, f"You are the agent for {phase_id}.", ["bash"]))

        # First iteration: real prompt
        await self._events.notify(notices.AgentBeforeSend(scope, f"Complete the work for {phase_id}.", 1))
        resp1 = _make_agent_response("I'll start working on this.")
        await self._events.notify(notices.AgentResponded(scope, resp1, 1))

        # Tool call
        tool_call = ToolCall(id=f"{phase_id}_tc1", name="bash", input={"cmd": "echo done"})
        tool_result = ToolResult(success=True, data="done\n")
        await self._events.notify(notices.ToolCalled(scope, tool_call, tool_result, 1))

        # Second iteration: model receives tool results instead of a user prompt.
        await self._events.notify(notices.AgentBeforeSend(scope, TOOL_RESULTS_SENTINEL, 2))
        resp2 = _make_agent_response("Work complete.")
        await self._events.notify(notices.AgentResponded(scope, resp2, 2))

        # Failure mode: fire error and raise before goal checks
        if self._fail_on_phase == phase_id:
            error = RuntimeError(f"Simulated failure in phase {phase_id!r}")
            await self._events.notify(notices.AgentErrored(scope, error))
            self.failed_phase = phase_id
            await self._events.notify(phase_notices.PhaseErrored(phase_id, error))
            await self._events.notify(RunErroredNotice())
            raise error

        # Goal validation for each task
        for task_name in task_names:
            await self._events.notify(phase_notices.BeforeGoalCheck(phase_id, task_name, 1))
            await self._events.notify(phase_notices.AfterGoalCheck(phase_id, task_name, 1, True, "Goal achieved."))

        react_result = _make_react_result(resp2)
        await self._events.notify(notices.AgentFinished(scope, react_result))
        await self._events.notify(phase_notices.PhaseFinished(phase_id))


def _make_builder(
    phases: list[tuple[str, list[str]]] | None = None,
    *,
    fail_on_phase: str | None = None,
) -> Any:
    """Return an orchestrator builder that creates a _FakeOrchestrator."""
    if phases is None:
        phases = DEMO_PHASES

    def builder(events: RunEvents) -> _FakeOrchestrator:
        return _FakeOrchestrator(events, phases, fail_on_phase=fail_on_phase)

    return builder


def _app(flow: ResolvedFlow | None = None) -> TogoApp:
    flow = flow or _make_flow()

    ddev_app = SimpleNamespace(
        config=SimpleNamespace(ai=SimpleNamespace(anthropic_api_key=None, flow_dirs=[])),
        repo=SimpleNamespace(path=str(Path.cwd())),
    )
    return TogoApp(
        engine=StaticConfigurationEngine([flow]),
        phase_registry=PhaseRegistry(),
        provider_registry=AgentProviderRegistry(),
        ddev_app=ddev_app,
    )


class _GraphHarness(Screen):
    def __init__(self, graph: Widget) -> None:
        super().__init__()
        self._graph = graph
        self.selected_phases: list[str] = []

    def compose(self) -> ComposeResult:
        yield self._graph

    def on_phase_selected(self, event: Any) -> None:
        self.selected_phases.append(event.phase_id)


# ---------------------------------------------------------------------------
# ExecutionScreen: builder injection and wiring
# ---------------------------------------------------------------------------


async def test_execution_screen_supports_background_notices():
    import asyncio

    from ddev.ai.run_events import Notice
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    delivered = asyncio.Event()

    async def receive(notice: Notice) -> None:
        delivered.set()

    class Orchestrator:
        def __init__(self, events: RunEvents) -> None:
            self.events = events
            events.subscribe(Notice, receive)

        async def run_async(self) -> None:
            await self.events.notify(Notice(), block=False)

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test():
        await app.push_screen(ExecutionScreen(flow, orchestrator_builder=Orchestrator))
        async with asyncio.timeout(5):
            await delivered.wait()


async def test_execution_screen_sets_bridge_target_on_mount():
    """ExecutionScreen sets app.bridge_target = itself on mount."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder())
        await app.push_screen(screen)
        await pilot.pause(0.1)
        assert app.bridge_target is screen


async def test_execution_screen_resets_bridge_target_on_unmount():
    """Popping ExecutionScreen resets app.bridge_target to the app."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(ExecutionScreen(flow, orchestrator_builder=_make_builder()))
        await pilot.pause(0.3)
        app.pop_screen()
        await pilot.pause(0.1)
        assert app.bridge_target is app


# ---------------------------------------------------------------------------
# ExecutionScreen: pipeline status transitions
# ---------------------------------------------------------------------------


async def test_pipeline_graph_renders_native_phase_nodes():
    """PipelineGraph renders phases as native widgets so TCSS can style each status."""
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PipelineGraph

    graph = PipelineGraph(_make_dag_flow(), {"research": RunStatus.RUNNING})
    app = _app(_make_dag_flow())
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(_GraphHarness(graph))
        await pilot.pause()
        nodes = {node.phase_id: node for node in graph.query("PhaseNode")}
        assert set(nodes) == {"research", "write_readme", "write_script", "write_tests", "final_review"}
        assert "status-running" in nodes["research"].classes
        assert "status-pending" in nodes["write_readme"].classes
        graph.query_one("#pipeline-connectors")


async def test_pipeline_graph_updates_phase_node_status_classes():
    """PipelineGraph updates native node classes when phase statuses change."""
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PipelineGraph

    graph = PipelineGraph(_make_dag_flow(), {"research": RunStatus.PENDING})
    app = _app(_make_dag_flow())
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(_GraphHarness(graph))
        await pilot.pause()
        graph.update_statuses({"research": RunStatus.DONE})
        await pilot.pause()
        node = {node.phase_id: node for node in graph.query("PhaseNode")}["research"]
        assert "status-done" in node.classes
        assert "status-pending" not in node.classes


async def test_phase_node_enter_selects_focused_phase_after_status_update():
    """Enter selects the focused phase after its status changes."""
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseNode, PipelineGraph

    graph = PipelineGraph(_make_dag_flow(), {"research": RunStatus.PENDING})
    harness = _GraphHarness(graph)
    app = _app(_make_dag_flow())
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(harness)
        await pilot.pause()
        graph.query_one(PhaseNode).focus()
        graph.update_statuses({"research": RunStatus.DONE})
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert harness.selected_phases == ["research"]


async def test_pipeline_graph_phase_node_click_ignores_text_selection(monkeypatch):
    """Releasing a drag selection over a phase node does not activate it."""
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseNode, PipelineGraph

    graph = PipelineGraph(_make_dag_flow(), {"research": RunStatus.PENDING})
    harness = _GraphHarness(graph)
    app = _app(_make_dag_flow())
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(harness)
        await pilot.pause()
        monkeypatch.setattr(harness, "get_selected_text", lambda: "selected phase text")

        graph.query_one(PhaseNode).on_click()
        await pilot.pause()

        assert harness.selected_phases == []


async def test_pipeline_nodes_start_pending():
    """All pipeline nodes start in 'pending' status."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    screen = ExecutionScreen(flow)
    for phase_id, _ in DEMO_PHASES:
        assert screen._phase_statuses[phase_id] is RunStatus.PENDING


def test_render_pipeline_draws_vertical_layered_dag():
    """Pipeline graph renders phase levels top-to-bottom with downward arrows."""
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import render_pipeline

    flow = _make_dag_flow()
    rendered = render_pipeline(flow, {entry.phase: RunStatus.PENDING for entry in flow.flow}).plain
    lines = rendered.splitlines()

    assert rendered.count("● research") == 1
    assert rendered.count("● write_readme") == 1
    assert rendered.count("● write_script") == 1
    assert rendered.count("● write_tests") == 1
    assert rendered.count("● final_review") == 1
    assert "▼" in rendered
    assert "▶" not in rendered
    assert next(i for i, line in enumerate(lines) if "● research" in line) < next(
        i for i, line in enumerate(lines) if "● final_review" in line
    )
    assert not any("● research" in line and "● write_readme" in line for line in lines)


async def test_pipeline_transitions_to_done_on_success():
    """All pipeline nodes reach 'done' after a successful _FakeOrchestrator run."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder())
        await app.push_screen(screen)
        await pilot.pause(0.5)

    for phase_id, _ in DEMO_PHASES:
        assert screen._phase_statuses[phase_id] is RunStatus.DONE, (
            f"Expected phase {phase_id!r} to be 'done', got {screen._phase_statuses[phase_id]!r}"
        )


async def test_pipeline_failed_phase_shows_failed_status():
    """A phase that raises shows 'failed' status; subsequent phases remain 'pending'."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(fail_on_phase="phase_1"))
        await app.push_screen(screen)
        await pilot.pause(0.5)

    assert screen._phase_statuses["phase_1"] is RunStatus.FAILED
    assert screen._phase_statuses["phase_2"] is RunStatus.PENDING


def test_interleaved_phase_error_only_mutates_scoped_phase() -> None:
    """An error from phase A cannot be attributed to concurrently running phase B."""
    from ddev.ai.agent.scope import AgentRole, AgentScope
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    screen = ExecutionScreen(_make_flow())
    screen.on_notice_message(NoticeMessage(phase_notices.PhaseStarted("phase_1")))
    screen.on_notice_message(NoticeMessage(phase_notices.PhaseStarted("phase_2")))
    phase_a_scope = AgentScope(owner_id="phase_1", role=AgentRole.PHASE, phase_id="phase_1")
    phase_b_scope = AgentScope(owner_id="phase_2", role=AgentRole.PHASE, phase_id="phase_2")
    screen.on_notice_message(NoticeMessage(notices.AgentBeforeSend(phase_a_scope, "phase A prompt", 1)))
    screen.on_notice_message(NoticeMessage(notices.AgentBeforeSend(phase_b_scope, "phase B prompt", 1)))

    screen.on_notice_message(NoticeMessage(notices.AgentErrored(phase_a_scope, RuntimeError("phase A failed"))))

    assert screen._phase_statuses["phase_1"] is RunStatus.FAILED
    assert screen._task_statuses[("phase_1", "task_one")] is RunStatus.FAILED
    assert screen._phase_statuses["phase_2"] is RunStatus.RUNNING
    assert screen._task_statuses[("phase_2", "task_two")] is RunStatus.PENDING
    assert any("phase A failed" in str(entry) for entry in screen._phase_logs["phase_1"])
    assert not any("phase A failed" in str(entry) for entry in screen._phase_logs["phase_2"])


def test_phase_error_is_written_in_full_to_failed_phase_log() -> None:
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    screen = ExecutionScreen(_make_flow())
    error = RuntimeError("first line\nfull validation detail\nhttps://errors.example.test/noise")

    screen.on_notice_message(NoticeMessage(phase_notices.PhaseErrored("phase_1", error)))

    assert screen._phase_statuses["phase_1"] is RunStatus.FAILED
    rendered = str(screen._phase_logs["phase_1"][-1])
    assert "first line" in rendered
    assert "full validation detail" in rendered
    assert "https://errors.example.test/noise" in rendered


def test_scoped_goal_event_only_mutates_identified_phase() -> None:
    """A goal verdict for phase A cannot update the same-named task in phase B."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow(phases=[("phase_1", ["shared_task"]), ("phase_2", ["shared_task"])])
    screen = ExecutionScreen(flow)
    screen.on_notice_message(NoticeMessage(phase_notices.PhaseStarted("phase_1")))
    screen.on_notice_message(NoticeMessage(phase_notices.PhaseStarted("phase_2")))

    screen.on_notice_message(NoticeMessage(phase_notices.BeforeGoalCheck("phase_1", "shared_task", 1)))
    screen.on_notice_message(NoticeMessage(phase_notices.BeforeGoalCheck("phase_2", "shared_task", 1)))
    screen.on_notice_message(NoticeMessage(phase_notices.AfterGoalCheck("phase_1", "shared_task", 1, True, "done")))

    assert screen._task_statuses[("phase_1", "shared_task")] is RunStatus.DONE
    assert screen._task_statuses[("phase_2", "shared_task")] is RunStatus.RUNNING

    screen.on_notice_message(NoticeMessage(phase_notices.AfterGoalCheck("phase_2", "shared_task", 1, False, "failed")))

    assert screen._task_statuses[("phase_1", "shared_task")] is RunStatus.DONE
    assert screen._task_statuses[("phase_2", "shared_task")] is RunStatus.FAILED


def test_context_cleared_notice_is_written_to_scoped_phase_log() -> None:
    from ddev.ai.agent.scope import AgentRole, AgentScope
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    screen = ExecutionScreen(flow)
    scope = AgentScope(owner_id="phase_1", role=AgentRole.PHASE, phase_id="phase_1")

    screen.on_notice_message(NoticeMessage(notices.ContextCleared(scope)))

    assert len(screen._phase_logs["phase_1"]) == 1
    assert "context cleared" in screen._phase_logs["phase_1"][0].plain.lower()
    assert screen._phase_logs["phase_2"] == []


async def test_pipeline_phase_running_during_execution():
    """A phase being run by _FakeOrchestrator transitions through 'running'."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()

    seen: list[str] = []

    def _builder_with_tracking(events: RunEvents) -> _FakeOrchestrator:
        async def record_start(notice: phase_notices.PhaseStarted) -> None:
            seen.append(f"start:{notice.phase_id}")

        async def record_finish(notice: phase_notices.PhaseFinished) -> None:
            seen.append(f"finish:{notice.phase_id}")

        events.subscribe(phase_notices.PhaseStarted, record_start)
        events.subscribe(phase_notices.PhaseFinished, record_finish)
        return _FakeOrchestrator(events, DEMO_PHASES)

    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=_builder_with_tracking)
        await app.push_screen(screen)
        await pilot.pause(0.5)

    assert "start:phase_1" in seen
    assert "finish:phase_1" in seen
    assert "start:phase_2" in seen
    assert "finish:phase_2" in seen


async def test_execution_phase_activation_opens_config_for_pending_phase():
    """Pending phase activation opens the shared phase configuration screen."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseSelected

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause()
        screen.on_phase_selected(PhaseSelected("phase_1"))
        await pilot.pause()
        assert isinstance(pilot.app.screen, PhaseConfigScreen)


async def test_execution_enter_opens_focused_phase_after_status_update():
    """A status update preserves keyboard activation of the focused phase."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseNode

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause()

        screen.query_one(PhaseNode).focus()
        screen.post_message(NoticeMessage(phase_notices.PhaseStarted("phase_1")))
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, PhaseLogScreen)
        assert app.screen.phase_id == "phase_1"


@pytest.mark.parametrize("status", [RunStatus.RUNNING, RunStatus.DONE])
async def test_execution_phase_activation_opens_log_for_started_phase(status: RunStatus):
    """Started phase activation opens a full-screen phase log."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseSelected

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause()
        screen._phase_statuses["phase_1"] = status
        screen.on_phase_selected(PhaseSelected("phase_1"))
        await pilot.pause()
        assert isinstance(pilot.app.screen, PhaseLogScreen)
        assert pilot.app.screen.phase_id == "phase_1"


async def test_execution_failed_phase_activation_opens_error_modal() -> None:
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.screens.phase_error_modal import PhaseErrorModal
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseSelected

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause()
        error = RuntimeError("first line\nfull validation detail")
        screen.on_notice_message(NoticeMessage(phase_notices.PhaseErrored("phase_1", error)))

        screen.on_phase_selected(PhaseSelected("phase_1"))
        await pilot.pause()

        assert isinstance(pilot.app.screen, PhaseErrorModal)
        assert pilot.app.screen.phase_id == "phase_1"
        rendered = str(pilot.app.screen.query_one("#phase-error-message", Static).render())
        assert "RuntimeError: first line" in rendered
        assert "full validation detail" in rendered

        await pilot.press("escape")
        await pilot.pause()
        assert pilot.app.screen is screen


async def test_execution_cancelled_phase_falls_back_to_log() -> None:
    import asyncio

    from ddev.ai.agent.scope import AgentRole, AgentScope
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseSelected

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause()
        scope = AgentScope(owner_id="phase_1", role=AgentRole.PHASE, phase_id="phase_1")
        screen.on_notice_message(NoticeMessage(notices.AgentErrored(scope, asyncio.CancelledError())))

        assert screen._phase_statuses["phase_1"] is RunStatus.FAILED
        assert "phase_1" not in screen._phase_errors

        screen.on_phase_selected(PhaseSelected("phase_1"))
        await pilot.pause()

        assert isinstance(pilot.app.screen, PhaseLogScreen)


async def test_phase_log_screen_ctrl_c_pushes_config_screen():
    """PhaseLogScreen exposes the shared config screen via ctrl+c."""
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(PhaseLogScreen(flow, "phase_1", []))
        await pilot.pause()
        await pilot.press("ctrl+c")
        await pilot.pause()
        assert isinstance(pilot.app.screen, PhaseConfigScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(pilot.app.screen, PhaseLogScreen)


async def test_phase_log_screen_ctrl_c_copies_selection_before_opening_config(monkeypatch):
    """Ctrl+C copies selected log text without navigating away."""
    from textual.geometry import Offset
    from textual.selection import Selection
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogBlock, PhaseLogScreen

    copied: list[str] = []
    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = PhaseLogScreen(flow, "phase_1", ["selected log output"])
        await app.push_screen(screen)
        await pilot.pause()
        text = screen.query_one(PhaseLogBlock).query_one(Static)
        screen.selections = {text: Selection(Offset(0, 0), None)}
        monkeypatch.setattr(app, "copy_to_clipboard", copied.append)

        await pilot.press("ctrl+c")
        await pilot.pause()

        assert app.screen is screen
        assert copied == ["selected log output"]


async def test_phase_log_screen_replays_entries_as_blocks_once():
    """Saved phase log entries are replayed as mounted block widgets."""
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogBlock, PhaseLogScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = PhaseLogScreen(flow, "phase_1", ["first log line"])
        await app.push_screen(screen)
        await pilot.pause()

        assert len(screen.query(PhaseLogBlock)) == 1

        assert screen._replay_entries() is True
        await pilot.pause()
        assert len(screen.query(PhaseLogBlock)) == 1


async def test_phase_log_renders_rich_markdown_as_selectable_textual_markdown():
    """Rich Markdown log entries become native Textual Markdown widgets."""
    from rich.markdown import Markdown as RichMarkdown
    from textual.geometry import Offset
    from textual.selection import Selection
    from textual.widgets import Markdown
    from textual.widgets.markdown import MarkdownBlock

    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogBlock, PhaseLogScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = PhaseLogScreen(flow, "phase_1", [RichMarkdown("copy **this response**")])
        await app.push_screen(screen)
        await pilot.pause()

        markdown = screen.query_one(PhaseLogBlock).query_one(Markdown)
        assert markdown.source == "copy **this response**"
        markdown_block = markdown.query_one(MarkdownBlock)
        screen.selections = {markdown_block: Selection(Offset(0, 0), None)}
        assert screen.get_selected_text() == "copy this response"


async def test_phase_log_renders_rich_panel_as_selectable_textual_panel():
    """Rich Panel log entries become bordered widgets with native selectable content."""
    from rich.markdown import Markdown as RichMarkdown
    from rich.panel import Panel
    from textual.geometry import Offset
    from textual.selection import Selection
    from textual.widgets import Markdown
    from textual.widgets.markdown import MarkdownBlock

    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogBlock, PhaseLogPanel, PhaseLogScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = PhaseLogScreen(
            flow,
            "phase_1",
            [Panel(RichMarkdown("copy the **prompt**"), title="prompt · agent")],
        )
        await app.push_screen(screen)
        await pilot.pause()

        panel = screen.query_one(PhaseLogBlock).query_one(PhaseLogPanel)
        assert panel.border_title == "prompt · agent"
        markdown = panel.query_one(Markdown)
        assert markdown.source == "copy the **prompt**"
        markdown_block = markdown.query_one(MarkdownBlock)
        screen.selections = {markdown_block: Selection(Offset(0, 0), None)}
        assert screen.get_selected_text() == "copy the prompt"


async def test_agent_output_routes_to_phase_logs_by_scope_phase_id():
    """Agent renderables are partitioned by AgentScope.phase_id."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder())
        await app.push_screen(screen)
        await pilot.pause(0.5)

    assert screen._phase_logs["phase_1"]
    assert screen._phase_logs["phase_2"]
    assert screen._phase_logs["phase_1"] is not screen._phase_logs["phase_2"]


async def test_phase_log_shows_thinking_block_until_agent_response():
    """Open phase logs show a transient component while an agent response is pending."""
    from ddev.ai.agent.scope import AgentRole, AgentScope
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen, ThinkingBlock

    class _IdleOrchestrator:
        async def run_async(self) -> None:
            pass

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=lambda _events: _IdleOrchestrator())
        await app.push_screen(screen)
        await pilot.pause()

        phase_log = PhaseLogScreen(flow, "phase_1", screen._phase_logs["phase_1"], source=screen)
        await app.push_screen(phase_log)
        await pilot.pause()

        scope = AgentScope(owner_id="phase_1", role=AgentRole.PHASE, phase_id="phase_1")
        screen.on_notice_message(NoticeMessage(notices.AgentBeforeSend(scope, "do the work", 1)))
        await pilot.pause()

        thinking_blocks = phase_log.query(ThinkingBlock)
        assert len(thinking_blocks) == 1
        assert "phase_1:phase:1" in screen._active_thinking["phase_1"]

        screen.on_notice_message(NoticeMessage(notices.AgentResponded(scope, _make_agent_response("done"), 1)))
        await pilot.pause()

        assert len(phase_log.query(ThinkingBlock)) == 0
        assert "phase_1:phase:1" not in screen._active_thinking["phase_1"]


async def test_sentinel_send_shows_thinking_without_prompt_block():
    """Sending tool results back to the model shows thinking without logging a fake prompt."""
    from ddev.ai.agent.scope import AgentRole, AgentScope
    from ddev.ai.react.process import TOOL_RESULTS_SENTINEL
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen, ThinkingBlock

    class _IdleOrchestrator:
        async def run_async(self) -> None:
            pass

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=lambda _events: _IdleOrchestrator())
        await app.push_screen(screen)
        await pilot.pause()

        phase_log = PhaseLogScreen(flow, "phase_1", screen._phase_logs["phase_1"], source=screen)
        await app.push_screen(phase_log)
        await pilot.pause()

        scope = AgentScope(owner_id="phase_1", role=AgentRole.PHASE, phase_id="phase_1")
        screen.on_notice_message(NoticeMessage(notices.AgentBeforeSend(scope, TOOL_RESULTS_SENTINEL, 2)))
        await pilot.pause()

        assert screen._phase_logs["phase_1"] == []
        assert len(phase_log.query(ThinkingBlock)) == 1

        screen.on_notice_message(NoticeMessage(notices.AgentResponded(scope, _make_agent_response("done"), 2)))
        await pilot.pause()

        assert len(phase_log.query(ThinkingBlock)) == 0


async def test_phase_log_replays_entries_before_active_thinking_block():
    """Opening a log mid-turn appends transient state after historical entries."""
    from ddev.ai.agent.scope import AgentRole, AgentScope
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogBlock, PhaseLogScreen, ThinkingBlock

    class _IdleOrchestrator:
        async def run_async(self) -> None:
            pass

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=lambda _events: _IdleOrchestrator())
        await app.push_screen(screen)
        await pilot.pause()

        scope = AgentScope(owner_id="phase_1", role=AgentRole.PHASE, phase_id="phase_1")
        screen.on_notice_message(NoticeMessage(notices.AgentBeforeSend(scope, "do the work", 1)))
        await pilot.pause()

        phase_log = PhaseLogScreen(flow, "phase_1", screen._phase_logs["phase_1"], source=screen)
        await app.push_screen(phase_log)
        await pilot.pause()

        output_children = list(phase_log.query_one("#phase-log-output").children)
        assert isinstance(output_children[-2], PhaseLogBlock)
        assert isinstance(output_children[-1], ThinkingBlock)


# ---------------------------------------------------------------------------
# ExecutionScreen: tasks panel
# ---------------------------------------------------------------------------


async def test_tasks_start_pending():
    """All tasks start in 'pending' status."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    screen = ExecutionScreen(flow)
    for phase_id, task_names in DEMO_PHASES:
        for task_name in task_names:
            assert screen._task_statuses[(phase_id, task_name)] is RunStatus.PENDING


async def test_tasks_done_after_success_run():
    """All tasks reach 'done' after a successful _FakeOrchestrator run."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder())
        await app.push_screen(screen)
        await pilot.pause(0.5)

    for phase_id, task_names in DEMO_PHASES:
        for task_name in task_names:
            key = (phase_id, task_name)
            assert screen._task_statuses[key] is RunStatus.DONE, (
                f"Expected task {key!r} to be 'done', got {screen._task_statuses[key]!r}"
            )


async def test_tasks_failed_when_phase_fails():
    """Tasks in a failed phase reach 'failed' status."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(fail_on_phase="phase_1"))
        await app.push_screen(screen)
        await pilot.pause(0.5)

    # phase_1 task should be failed
    assert screen._task_statuses[("phase_1", "task_one")] is RunStatus.FAILED
    # phase_2 task should remain pending
    assert screen._task_statuses[("phase_2", "task_two")] is RunStatus.PENDING


# ---------------------------------------------------------------------------
# ExecutionScreen: renderable output produced by the orchestrator
# ---------------------------------------------------------------------------


async def test_output_records_rendered_output():
    """Output renderables are recorded as the orchestrator runs."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder())
        await app.push_screen(screen)
        await pilot.pause(0.5)

    assert screen._output_write_count > 0


async def test_phase_log_output_uses_block_scroll_container():
    """Phase log output is a component container, not an append-only RichLog."""
    from textual.containers import VerticalScroll

    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        await app.push_screen(PhaseLogScreen(flow, "phase_1", []))
        await pilot.pause()
        output = pilot.app.screen.query_one("#phase-log-output", VerticalScroll)
        assert output.border_title is None


async def test_output_includes_prompt_panel():
    """Recorded output includes a Rich Panel with Markdown prompt content."""
    from rich.markdown import Markdown
    from rich.panel import Panel

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder())
        await app.push_screen(screen)
        await pilot.pause(0.5)

    panels = [r for r in screen._output_renders if isinstance(r, Panel)]
    assert len(panels) >= len(DEMO_PHASES), (
        f"Expected at least {len(DEMO_PHASES)} Panel(s) in output, got {len(panels)}"
    )
    assert all(isinstance(panel.renderable, Markdown) for panel in panels)


async def test_output_renders_agent_responses_as_markdown():
    """Agent response bodies are written as Markdown renderables."""
    from rich.markdown import Markdown

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder())
        await app.push_screen(screen)
        await pilot.pause(0.5)

    responses = [r for r in screen._output_renders if isinstance(r, Markdown)]
    assert len(responses) >= len(DEMO_PHASES)


async def test_output_contains_agent_start_header():
    """Recorded output includes agent start headers (Rich Text objects)."""
    from rich.text import Text

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder())
        await app.push_screen(screen)
        await pilot.pause(0.5)

    texts = [r for r in screen._output_renders if isinstance(r, Text)]
    assert len(texts) > 0


# ---------------------------------------------------------------------------
# ExecutionScreen: execution lifecycle
# ---------------------------------------------------------------------------


async def test_execution_finishes_phases_before_reporting_success() -> None:
    """All-green phases show finishing until the orchestrator returns cleanly."""
    import asyncio

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.widgets.header import ExecutionStatusBadge

    release = asyncio.Event()

    class ControlledOrchestrator:
        failed_phase = None

        def __init__(self, events: RunEvents) -> None:
            self.events = events

        async def run_async(self) -> None:
            for phase_id, _ in DEMO_PHASES:
                await self.events.notify(phase_notices.PhaseFinished(phase_id))
            await release.wait()

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=ControlledOrchestrator)
        await app.push_screen(screen)
        await pilot.pause()

        badge = screen.query_one(ExecutionStatusBadge)
        assert str(badge.render()) == "◌ finishing"

        release.set()
        await pilot.pause()

        assert str(badge.render()) == "✓ completed"


async def test_execution_failure_during_finalization_never_reports_success() -> None:
    """A failure after all phases finish replaces finishing with a failed result."""
    import asyncio

    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.widgets.header import ExecutionStatusBadge

    release = asyncio.Event()

    class FailingFinalizer:
        failed_phase = None

        def __init__(self, events: RunEvents) -> None:
            self.events = events

        async def run_async(self) -> None:
            for phase_id, _ in DEMO_PHASES:
                await self.events.notify(phase_notices.PhaseFinished(phase_id))
            await release.wait()
            raise RuntimeError("finalization failed")

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=FailingFinalizer)
        await app.push_screen(screen)
        await pilot.pause()

        badge = screen.query_one(ExecutionStatusBadge)
        assert str(badge.render()) == "◌ finishing"

        release.set()
        await pilot.pause()

        error = screen.query_one("#execution-error", Static)
        assert str(badge.render()) == "✕ failed"
        assert "finalization failed" in str(error.render())


async def test_phase_log_header_keeps_running_status() -> None:
    """Opening a phase log keeps the active flow status visible."""
    import asyncio

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.phase_log import PhaseLogScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseNode

    release = asyncio.Event()

    class RunningPhase:
        failed_phase = None

        def __init__(self, events: RunEvents) -> None:
            self.events = events

        async def run_async(self) -> None:
            await self.events.notify(phase_notices.PhaseStarted("phase_1"))
            await release.wait()

    flow = _make_flow()
    app = _app(flow)
    app.animation_level = "none"
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=RunningPhase)
        await app.push_screen(screen)
        await pilot.pause()

        screen.query_one(PhaseNode).focus()
        await pilot.press("enter")
        await pilot.pause()

        assert isinstance(app.screen, PhaseLogScreen)
        assert "● running" in export_screenshot_text(app)

        release.set()
        await pilot.pause()
        assert "✓ completed" in export_screenshot_text(app)


# ---------------------------------------------------------------------------
# ExecutionScreen: cancellation
# ---------------------------------------------------------------------------


async def test_cancel_stops_worker_without_crash():
    """Ctrl+C cancels the run without reporting successful completion."""
    import asyncio

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.widgets.header import ExecutionStatusBadge

    cancelled = asyncio.Event()

    class _InfiniteDemo:
        failed_phase = None

        async def run_async(self) -> None:
            try:
                await asyncio.sleep(999)
            except asyncio.CancelledError:
                cancelled.set()
                raise

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=lambda _events: _InfiniteDemo())
        await app.push_screen(screen)
        await pilot.pause(0.05)
        await pilot.press("ctrl+c")
        await pilot.pause()

        assert pilot.app.is_running
        assert cancelled.is_set()
        assert str(screen.query_one(ExecutionStatusBadge).render()) == ""


async def test_execution_ctrl_c_copies_selection_before_cancelling(monkeypatch):
    """Ctrl+C copies selected text without cancelling the active run."""
    import asyncio

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    class _InfiniteDemo:
        async def run_async(self) -> None:
            await asyncio.sleep(999)

    copied: list[str] = []
    cancelled: list[bool] = []
    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=lambda _events: _InfiniteDemo())
        await app.push_screen(screen)
        await pilot.pause()
        assert screen._run_worker is not None
        monkeypatch.setattr(screen, "get_selected_text", lambda: "selected pipeline output")
        monkeypatch.setattr(screen._run_worker, "cancel", lambda: cancelled.append(True))
        monkeypatch.setattr(app, "copy_to_clipboard", copied.append)

        screen.action_copy_or_cancel_run()

        assert copied == ["selected pipeline output"]
        assert cancelled == []


async def test_unmount_cancels_worker():
    """Popping ExecutionScreen cancels the worker."""
    import asyncio

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    class _InfiniteDemo:
        failed_phase = None

        async def run_async(self) -> None:
            await asyncio.sleep(999)

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=lambda _events: _InfiniteDemo())
        await app.push_screen(screen)
        await pilot.pause(0.05)
        app.pop_screen()
        await pilot.pause(0.1)
        assert isinstance(pilot.app.screen, MainScreen)
        assert pilot.app.is_running


async def test_escape_requires_confirmation_before_cancelling_active_run():
    """Escape keeps an active run alive until the destructive action is confirmed."""
    import asyncio

    from ddev.cli.meta.ai.tui.screens.cancel_run_modal import CancelRunModal
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    cancelled = asyncio.Event()

    class _InfiniteDemo:
        failed_phase = None

        async def run_async(self) -> None:
            try:
                await asyncio.sleep(999)
            except asyncio.CancelledError:
                cancelled.set()
                raise

    flow = _make_flow()
    app = _app(flow)
    app.animation_level = "none"
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=lambda _events: _InfiniteDemo())
        await app.push_screen(screen)
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, CancelRunModal)
        assert not cancelled.is_set()

        await pilot.press("escape")
        await pilot.pause()
        assert app.screen is screen
        assert not cancelled.is_set()

        await pilot.press("escape")
        await pilot.pause()
        await pilot.click("#btn-cancel-flow")
        await pilot.pause()
        assert isinstance(app.screen, MainScreen)
        assert cancelled.is_set()


async def test_back_pops_immediately_after_run_finishes():
    """Back does not prompt once the worker has finished."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.widgets.header import ExecutionStatusBadge

    class _FinishedDemo:
        failed_phase = None

        async def run_async(self) -> None:
            return

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=lambda _events: _FinishedDemo())
        await app.push_screen(screen)
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        assert isinstance(app.screen, MainScreen)
        assert str(app.screen.query_one(ExecutionStatusBadge).render()) == ""


# ---------------------------------------------------------------------------
# ExecutionScreen: failing orchestrator does not crash the app
# ---------------------------------------------------------------------------


async def test_failing_orchestrator_no_app_crash():
    """A raising orchestrator surfaces failure in UI without crashing the app."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen
    from ddev.cli.meta.ai.tui.widgets.header import ExecutionStatusBadge

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(fail_on_phase="phase_1"))
        await app.push_screen(screen)
        await pilot.pause(0.5)
        assert pilot.app.is_running
        assert isinstance(pilot.app.screen, ExecutionScreen)
        assert str(screen.query_one(ExecutionStatusBadge).render()) == "✕ failed"


async def test_orchestrator_build_failure_is_visible_and_screen_stays_stable() -> None:
    """Startup failures are rendered even though the worker does not exit on error."""
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.widgets.header import ExecutionStatusBadge

    def fail_to_build(_events: RunEvents) -> Any:
        raise RuntimeError("constructor exploded")

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=fail_to_build)
        await app.push_screen(screen)
        await pilot.pause()

        error = screen.query_one("#execution-error", Static)
        assert error.display
        assert "constructor exploded" in str(error.render())
        assert str(screen.query_one(ExecutionStatusBadge).render()) == "✕ failed"
        assert app.screen is screen
        assert app.is_running


async def test_phase_error_notice_only_marks_reported_failed_phase() -> None:
    """A phase failure notice fails its phase without attributing the error to a concurrent sibling."""
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    class ConcurrentFailure:
        failed_phase = "phase_1"

        def __init__(self, events: RunEvents) -> None:
            self.events = events

        async def run_async(self) -> None:
            await self.events.notify(phase_notices.PhaseStarted("phase_1"))
            await self.events.notify(phase_notices.PhaseStarted("phase_2"))
            error = RuntimeError("phase 1 crashed")
            await self.events.notify(phase_notices.PhaseErrored("phase_1", error))
            await self.events.notify(RunErroredNotice())
            raise error

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=ConcurrentFailure)
        await app.push_screen(screen)
        await pilot.pause()

        assert screen._phase_statuses["phase_1"] is RunStatus.FAILED
        assert screen._task_statuses[("phase_1", "task_one")] is RunStatus.FAILED
        assert screen._phase_statuses["phase_2"] is RunStatus.RUNNING
        assert screen._task_statuses[("phase_2", "task_two")] is RunStatus.PENDING
        assert "Run failed in phase_1: phase 1 crashed" in str(screen.query_one("#execution-error", Static).render())


@pytest.mark.parametrize(
    ("startup", "title"),
    [(True, "AI Gateway login failed"), (False, "Credential refresh failed")],
    ids=["startup", "mid-run"],
)
async def test_gateway_credential_failure_opens_recovery_modal(startup, title):
    from textual.widgets import Static

    from ddev.ai.model_catalog import Route
    from ddev.ai.runtime.errors import CredentialRefreshError, RefreshFailureCause
    from ddev.ai.runtime.gateway_auth import gateway_refresh_error
    from ddev.cli.meta.ai.tui.screens.credential_refresh_modal import CredentialRefreshModal
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    class FailedCredentialAcquisition:
        failed_phase = None if startup else "phase_1"

        def __init__(self, events: RunEvents) -> None:
            self.events = events

        async def run_async(self) -> None:
            cause = RefreshFailureCause.LOGIN_TIMED_OUT
            if self.failed_phase is None:
                raise CredentialRefreshError(Route.AI_GATEWAY, cause, "AI Gateway startup failed.", (), startup=True)
            await self.events.notify(phase_notices.PhaseStarted(self.failed_phase))
            error = gateway_refresh_error(cause)
            await self.events.notify(phase_notices.PhaseErrored(self.failed_phase, error))
            await self.events.notify(RunErroredNotice())
            raise error

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        screen = ExecutionScreen(flow, orchestrator_builder=FailedCredentialAcquisition)
        await app.push_screen(screen)
        await pilot.pause()

        assert isinstance(app.screen, CredentialRefreshModal)
        assert str(app.screen.query_one("#dialog").border_title) == title
        if not startup:
            message = str(app.screen.query_one("#credential-refresh-message", Static).render())
            assert "This run uses the AI Gateway" in message
            assert "could not be refreshed" in message
            assert "Run dd-auth -- true in a terminal" in message
            assert "browser" in message and "curl instructions" in message
            assert "ddev meta ai, select the flow, then choose Resume" in message
            assert "Completed phases are kept" in message
            assert "starts again from its first task and may redo work" in message

        await pilot.click("#btn-close")
        assert app.screen is screen


async def test_orchestrator_exception_without_failed_phase_is_not_attributed() -> None:
    """An unknown orchestration failure is visible without failing concurrent phases."""
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    class UnknownFailure:
        failed_phase = None

        def __init__(self, events: RunEvents) -> None:
            self.events = events

        async def run_async(self) -> None:
            await self.events.notify(phase_notices.PhaseStarted("phase_1"))
            await self.events.notify(phase_notices.PhaseStarted("phase_2"))
            raise RuntimeError("scheduler crashed")

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=UnknownFailure)
        await app.push_screen(screen)
        await pilot.pause()

        assert screen._phase_statuses["phase_1"] is RunStatus.RUNNING
        assert screen._phase_statuses["phase_2"] is RunStatus.RUNNING
        assert screen._task_statuses[("phase_1", "task_one")] is RunStatus.PENDING
        assert screen._task_statuses[("phase_2", "task_two")] is RunStatus.PENDING
        assert "scheduler crashed" in str(screen.query_one("#execution-error", Static).render())


async def test_run_error_banner_is_compact_and_points_to_phase_log() -> None:
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause()

        screen.on_notice_message(
            NoticeMessage(
                phase_notices.PhaseErrored(
                    "phase_1",
                    RuntimeError("invalid input\nfull validation detail\nhttps://errors.example"),
                )
            )
        )
        screen.on_notice_message(NoticeMessage(RunErroredNotice()))

        banner = str(screen.query_one("#execution-error", Static).render())
        assert "Run failed in phase_1: invalid input" in banner
        assert "Select phase_1 to view the full error." in banner
        assert "full validation detail" not in banner
        assert "https://errors.example" not in banner


async def test_run_error_banner_aggregates_parallel_phase_errors() -> None:
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause()

        screen.on_notice_message(
            NoticeMessage(phase_notices.PhaseErrored("phase_1", RuntimeError("alpha failed\nalpha details")))
        )
        screen.on_notice_message(
            NoticeMessage(phase_notices.PhaseErrored("phase_2", RuntimeError("beta failed\nbeta details")))
        )
        screen.on_notice_message(NoticeMessage(RunErroredNotice()))

        banner = str(screen.query_one("#execution-error", Static).render())
        assert "Run failed — 2 phases failed" in banner
        assert "phase_1: alpha failed" in banner
        assert "phase_2: beta failed" in banner
        assert "alpha details" not in banner
        assert "beta details" not in banner


async def test_late_parallel_phase_error_updates_existing_banner() -> None:
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause()

        screen.on_notice_message(NoticeMessage(phase_notices.PhaseErrored("phase_1", RuntimeError("alpha failed"))))
        screen.on_notice_message(NoticeMessage(RunErroredNotice()))
        screen.on_notice_message(NoticeMessage(phase_notices.PhaseErrored("phase_2", RuntimeError("beta failed"))))

        banner = str(screen.query_one("#execution-error", Static).render())
        assert "Run failed — 2 phases failed" in banner
        assert "phase_1: alpha failed" in banner
        assert "phase_2: beta failed" in banner


# ---------------------------------------------------------------------------
# ExecutionScreen: resume mode skips completed phases
# ---------------------------------------------------------------------------


async def test_resume_flag_passed_to_orchestrator():
    """ExecutionScreen stores resume=True and passes it to the builder."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()

    def _builder(_events: RunEvents) -> Any:
        class _Noop:
            async def run_async(self) -> None:
                pass

        return _Noop()

    screen = ExecutionScreen(flow, resume=True, orchestrator_builder=_builder)
    assert screen.resume is True


async def test_resume_initializes_completed_phase_statuses(tmp_path: Path) -> None:
    """Dependency-closed checkpoint successes render done before resumed work starts."""
    from ddev.cli.meta.ai.tui.runs import flow_slug
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_dag_flow()
    run_dir = tmp_path / flow_slug(flow)
    run_dir.mkdir()
    (run_dir / "checkpoints.yaml").write_text(
        """research:
  status: success
  started_at: '2024-01-01T00:00:00'
  finished_at: '2024-01-01T00:01:00'
  tokens: {total_input: 1, total_output: 1}
  memory_path: research_memory.md
final_review:
  status: success
  started_at: '2024-01-01T00:00:00'
  finished_at: '2024-01-01T00:01:00'
  tokens: {total_input: 1, total_output: 1}
  memory_path: final_review_memory.md
"""
    )

    class Noop:
        failed_phase = None

        async def run_async(self) -> None:
            pass

    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(flow, resume=True, runs_dir=tmp_path, orchestrator_builder=lambda _events: Noop())
        await app.push_screen(screen)
        await pilot.pause()

        assert screen._phase_statuses["research"] is RunStatus.DONE
        assert screen._phase_statuses["final_review"] is RunStatus.PENDING


async def test_resume_transitions_to_finishing_after_remaining_phase(tmp_path: Path) -> None:
    """A resumed done phase participates in the all-green finishing check."""
    import asyncio

    from ddev.cli.meta.ai.tui.runs import flow_slug
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    run_dir = tmp_path / flow_slug(flow)
    run_dir.mkdir()
    (run_dir / "checkpoints.yaml").write_text(
        """phase_1:
  status: success
  started_at: '2024-01-01T00:00:00'
  finished_at: '2024-01-01T00:01:00'
  tokens: {total_input: 1, total_output: 1}
  memory_path: phase_1_memory.md
"""
    )
    release = asyncio.Event()

    class ResumeOrchestrator:
        failed_phase = None

        def __init__(self, events: RunEvents) -> None:
            self.events = events

        async def run_async(self) -> None:
            await self.events.notify(phase_notices.PhaseFinished("phase_2"))
            await release.wait()

    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = ExecutionScreen(
            flow,
            resume=True,
            runs_dir=tmp_path,
            orchestrator_builder=ResumeOrchestrator,
        )
        await app.push_screen(screen)
        await pilot.pause()

        from ddev.cli.meta.ai.tui.widgets.header import ExecutionStatusBadge

        assert str(screen.query_one(ExecutionStatusBadge).render()) == "◌ finishing"
        release.set()
        await pilot.pause()
        assert str(screen.query_one(ExecutionStatusBadge).render()) == "✓ completed"


# ---------------------------------------------------------------------------
# NEW: Default builder constructs real PhaseOrchestrator — TDD tests
# These tests verify end-to-end wiring of the real orchestrator path.
# ---------------------------------------------------------------------------


def _setup_default_builder_mocks(tmp_path: Path):
    """Return (fake_ddev_app, mock_orch_instance) for default-builder tests."""
    from unittest.mock import AsyncMock, MagicMock

    fake_ddev_app = MagicMock()
    fake_ddev_app.config.ai.anthropic_api_key = "test_api_key_abc"
    fake_ddev_app.repo.path = str(tmp_path)

    mock_orch_instance = MagicMock()
    mock_orch_instance.run_async = AsyncMock()
    return fake_ddev_app, mock_orch_instance


def _app_with_repo(flow: ResolvedFlow, ddev_app: Any) -> TogoApp:
    return TogoApp(
        engine=StaticConfigurationEngine([flow]),
        phase_registry=PhaseRegistry(),
        provider_registry=AgentProviderRegistry(),
        ddev_app=ddev_app,
    )


async def test_default_builder_constructs_real_phase_orchestrator(tmp_path: Path) -> None:
    """Default builder constructs a real PhaseOrchestrator wired with correct params."""
    from unittest.mock import patch

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    fake_ddev_app, mock_orch_instance = _setup_default_builder_mocks(tmp_path)

    with patch("ddev.ai.runtime.orchestrator.PhaseOrchestrator") as MockOrch:
        MockOrch.return_value = mock_orch_instance
        togo_app = _app_with_repo(flow, fake_ddev_app)
        async with togo_app.run_test() as pilot:
            await pilot.pause()
            screen = ExecutionScreen(flow, runtime_variables={"integration": "My Integration"})
            await togo_app.push_screen(screen)
            await pilot.pause(0.3)

    MockOrch.assert_called_once()
    call_kwargs = MockOrch.call_args.kwargs
    assert call_kwargs["resolved_flow"] is flow
    assert call_kwargs["phase_registry"] is togo_app.phase_registry
    assert call_kwargs["provider_registry"] is togo_app.provider_registry
    assert call_kwargs["resume"] is False

    from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

    assert isinstance(call_kwargs["file_access_policy"], FileAccessPolicy)
    assert call_kwargs["file_access_policy"].write_root == tmp_path


async def test_default_builder_resume_flag_forwarded(tmp_path: Path) -> None:
    """Default builder forwards resume=True to PhaseOrchestrator."""
    from unittest.mock import patch

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    fake_ddev_app, mock_orch_instance = _setup_default_builder_mocks(tmp_path)

    with patch("ddev.ai.runtime.orchestrator.PhaseOrchestrator") as MockOrch:
        MockOrch.return_value = mock_orch_instance
        togo_app = _app_with_repo(flow, fake_ddev_app)
        async with togo_app.run_test() as pilot:
            await pilot.pause()
            screen = ExecutionScreen(flow, resume=True, runtime_variables={"integration": "My Integration"})
            await togo_app.push_screen(screen)
            await pilot.pause(0.3)

    call_kwargs = MockOrch.call_args.kwargs
    assert call_kwargs["resume"] is True


async def test_default_builder_forwards_runtime_variables(tmp_path: Path) -> None:
    """Default builder forwards runtime variables to PhaseOrchestrator unchanged."""
    from unittest.mock import patch

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    fake_ddev_app, mock_orch_instance = _setup_default_builder_mocks(tmp_path)

    with patch("ddev.ai.runtime.orchestrator.PhaseOrchestrator") as MockOrch:
        MockOrch.return_value = mock_orch_instance
        togo_app = _app_with_repo(flow, fake_ddev_app)
        async with togo_app.run_test() as pilot:
            await pilot.pause()
            screen = ExecutionScreen(flow, runtime_variables={"max_timeout": "120", "integration": "My Integration"})
            await togo_app.push_screen(screen)
            await pilot.pause(0.3)

    call_kwargs = MockOrch.call_args.kwargs
    assert call_kwargs["runtime_variables"] == {"max_timeout": "120", "integration": "My Integration"}


async def test_fresh_real_run_clears_only_computed_flow_directory(tmp_path: Path):
    """A fresh run removes stale state for its flow without touching sibling runs."""
    from ddev.cli.meta.ai.tui.runs import ai_runs_dir, flow_slug
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow(phases=[])
    flow.agents.clear()
    run_root = ai_runs_dir(tmp_path)
    run_dir = run_root / flow_slug(flow)
    sibling = run_root / "other-flow"
    run_dir.mkdir(parents=True)
    sibling.mkdir()
    (run_dir / "checkpoints.yaml").write_text("stale")
    (run_dir / "phase_1_memory.md").write_text("secret")
    (run_dir / "agent.log").write_text("old")
    (sibling / "keep.txt").write_text("keep")
    fake_ddev_app, _ = _setup_default_builder_mocks(tmp_path)

    app = _app_with_repo(flow, fake_ddev_app)
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(ExecutionScreen(flow, runtime_variables={"integration": "test"}))
        await pilot.pause()

    assert run_dir.is_dir()
    assert list(run_dir.iterdir()) == []
    assert (sibling / "keep.txt").read_text() == "keep"


async def test_resume_real_run_preserves_existing_flow_directory(tmp_path: Path):
    """Resume never clears checkpoint, memory, or agent-log state."""
    from ddev.cli.meta.ai.tui.runs import ai_runs_dir, flow_slug
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow(phases=[])
    flow.agents.clear()
    run_dir = ai_runs_dir(tmp_path) / flow_slug(flow)
    run_dir.mkdir(parents=True)
    stale = run_dir / "agent.log"
    stale.write_text("keep")
    fake_ddev_app, _ = _setup_default_builder_mocks(tmp_path)

    app = _app_with_repo(flow, fake_ddev_app)
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(ExecutionScreen(flow, resume=True, runtime_variables={"integration": "test"}))
        await pilot.pause()

    assert stale.read_text() == "keep"


async def test_fresh_real_run_refuses_run_root_symlink_outside_repo(tmp_path: Path) -> None:
    """Cleanup cannot follow a repository run-root symlink into another directory."""
    from unittest.mock import patch

    from ddev.cli.meta.ai.tui.runs import flow_slug
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen

    flow = _make_flow()
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside_run = outside / flow_slug(flow)
    outside_run.mkdir(parents=True)
    keep = outside_run / "keep.txt"
    keep.write_text("keep")
    (tmp_path / ".ddev").mkdir()
    (tmp_path / ".ddev" / "ai-runs").symlink_to(outside, target_is_directory=True)
    fake_ddev_app, mock_orch_instance = _setup_default_builder_mocks(tmp_path)

    with patch("ddev.ai.runtime.orchestrator.PhaseOrchestrator", return_value=mock_orch_instance) as mock_orch:
        app = _app_with_repo(flow, fake_ddev_app)
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(ExecutionScreen(flow))
            await pilot.pause()

    assert keep.read_text() == "keep"
    mock_orch.assert_not_called()


async def test_launch_from_flow_screen_no_runtime_error(tmp_path: Path) -> None:
    """Launching from FlowScreen passes the resolved flow into execution."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

    flow = _make_flow()

    fake_ddev_app = MagicMock()
    fake_ddev_app.config.ai.anthropic_api_key = "launch_test_key"
    fake_ddev_app.repo.path = str(tmp_path)

    mock_orch_instance = MagicMock()
    mock_orch_instance.run_async = AsyncMock()

    with patch("ddev.ai.runtime.orchestrator.PhaseOrchestrator") as MockOrch:
        MockOrch.return_value = mock_orch_instance
        togo_app = _app_with_repo(flow, fake_ddev_app)
        async with togo_app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            await togo_app.push_screen(FlowScreen(flow))
            await pilot.pause()
            await pilot.click("#launch-btn")
            await pilot.pause()
            prd = tmp_path / "prd.md"
            prd.write_text("Required product behavior.\n", encoding="utf-8")
            pilot.app.screen.query_one("#input-prd", Input).value = str(prd)
            await pilot.click("#btn-launch")
            await pilot.pause(0.3)
            assert isinstance(pilot.app.screen, ExecutionScreen)
            assert pilot.app.is_running

    # The real orchestrator was constructed (not a RuntimeError path)
    MockOrch.assert_called_once()


async def test_phase_config_renders_inlined_agent_prompt() -> None:
    """PhaseConfigScreen shows the system prompt already inlined by resolution."""
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

    flow = _make_flow()
    first_phase = flow.flow[0].phase
    first_agent = flow.phases[first_phase].agent
    assert first_agent is not None
    flow.agents[first_agent].system_prompt = "Inlined system prompt"

    app = _app(flow)
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.push_screen(PhaseConfigScreen(flow, first_phase))
        await pilot.pause()

        prompt_widget = pilot.app.screen.query_one("#phase-agent-prompt")
        assert "Inlined system prompt" in prompt_widget.source


# ---------------------------------------------------------------------------
# Missing edge case: ExecutionScreen with zero phases
# ---------------------------------------------------------------------------


async def test_execution_screen_empty_flow() -> None:
    """ExecutionScreen with zero phases mounts without error."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow(phases=[])
    app = _app(flow)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)
        screen = ExecutionScreen(flow, orchestrator_builder=_make_builder(phases=[]))
        await app.push_screen(screen)
        await pilot.pause(0.5)
        assert pilot.app.is_running

    # No phases → statuses dict is empty and all phases are trivially "done"
    assert screen._phase_statuses == {}
