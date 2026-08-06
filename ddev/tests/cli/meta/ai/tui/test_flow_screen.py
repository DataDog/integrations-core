# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for FlowScreen content, agent modal activation, launch wiring, and resume affordance."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from textual.containers import Horizontal
from textual.widgets import Button, Input

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
from ddev.ai.phases.registry import PhaseRegistry
from ddev.cli.meta.ai.tui.app import TogoApp

from .conftest import StaticConfigurationEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flow(name: str = "Test Flow", n_phases: int = 2) -> ResolvedFlow:
    """Create a minimal ResolvedFlow with *n_phases* entries."""
    agents = {"agent_a": AgentConfig.model_construct(provider="anthropic", tools=[])}
    phases = {
        f"phase_{i}": PhaseConfig(
            name=f"phase_{i}",
            agent="agent_a",
            tasks=[TaskConfig(name=f"task_{i}", prompt="do something")],
        )
        for i in range(n_phases)
    }
    flow = [FlowEntry(phase=f"phase_{i}") for i in range(n_phases)]
    return ResolvedFlow(
        name=name,
        description=f"Description for {name}",
        inputs=FlowConfig(name="test", flow=[]).inputs,
        agents=agents,
        phases=phases,
        flow=flow,
        variables={},
    )


def _app() -> TogoApp:
    flow = _make_flow()
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


def _provide_prd(screen, tmp_path: Path) -> str:
    """Populate the required built-in PRD input and return its content."""
    content = "Required product behavior.\n"
    prd_path = tmp_path / "prd.md"
    prd_path.write_text(content, encoding="utf-8")
    screen.query_one("#input-prd", Input).value = str(prd_path)
    return content


def _success_checkpoint_yaml(phase: str) -> str:
    """Return a success checkpoint block for one phase."""
    return f"""{phase}:
  status: success
  started_at: '2024-01-01T00:00:00'
  finished_at: '2024-01-01T00:01:00'
  tokens:
    total_input: 100
    total_output: 100
  memory_path: {phase}_memory.md
"""


def _write_run(tmp_path: Path, flow: ResolvedFlow, checkpoints_yaml: str) -> Path:
    """Write *checkpoints_yaml* to the run dir for *flow* below tmp_path."""
    from ddev.cli.meta.ai.tui.runs import flow_slug

    run_dir = tmp_path / flow_slug(flow)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "checkpoints.yaml").write_text(checkpoints_yaml)
    return tmp_path


def _write_incomplete_run(tmp_path: Path, flow: ResolvedFlow) -> Path:
    """Create a run dir under tmp_path with only the first scheduled phase at success."""
    return _write_run(tmp_path, flow, _success_checkpoint_yaml(flow.flow[0].phase))


def _write_complete_run(tmp_path: Path, flow: ResolvedFlow) -> Path:
    """Create a run dir under tmp_path with every scheduled phase at success."""
    return _write_run(tmp_path, flow, "".join(_success_checkpoint_yaml(entry.phase) for entry in flow.flow))


def _assert_no_resume_state(flow: ResolvedFlow, runs_dir: Path) -> None:
    """Used to assert *flow* records nothing at all below *runs_dir*."""
    from ddev.ai.runtime.checkpoints import ResumeState
    from ddev.cli.meta.ai.tui.runs import flow_resume_state

    assert flow_resume_state(flow, runs_dir=runs_dir) == ResumeState()


# ---------------------------------------------------------------------------
# Resumable-run helper unit tests
# ---------------------------------------------------------------------------


def test_flow_slug_distinguishes_case_sensitive_names() -> None:
    """Case-distinct flow names cannot share persisted run state."""
    from ddev.cli.meta.ai.tui.runs import flow_slug

    upper = flow_slug(_make_flow(name="Build"))
    lower = flow_slug(_make_flow(name="build"))
    assert upper != lower
    assert upper.startswith("build-")
    assert lower.startswith("build-")


def test_flow_resume_state_no_dir(tmp_path: Path) -> None:
    """No run dir → not resumable."""
    from ddev.cli.meta.ai.tui.runs import flow_resume_state

    flow = _make_flow()
    assert not flow_resume_state(flow, runs_dir=tmp_path).is_resumable


def test_flow_resume_state_incomplete_checkpoints(tmp_path: Path) -> None:
    """Run dir with incomplete checkpoints → resumable."""
    from ddev.cli.meta.ai.tui.runs import flow_resume_state

    flow = _make_flow(n_phases=2)
    _write_incomplete_run(tmp_path, flow)
    state = flow_resume_state(flow, runs_dir=tmp_path)
    assert state.is_resumable
    assert state.completed == {flow.flow[0].phase}


def test_flow_resume_state_all_phases_complete(tmp_path: Path) -> None:
    """All scheduled phases at success → not resumable."""
    from ddev.cli.meta.ai.tui.runs import flow_resume_state

    flow = _make_flow(n_phases=2)
    _write_complete_run(tmp_path, flow)
    state = flow_resume_state(flow, runs_dir=tmp_path)
    assert state.completed == {entry.phase for entry in flow.flow}
    assert not state.is_resumable


def test_flow_resume_state_no_checkpoints_file(tmp_path: Path) -> None:
    """Run dir exists but no checkpoints.yaml → not resumable."""
    from ddev.cli.meta.ai.tui.runs import flow_slug

    flow = _make_flow()
    (tmp_path / flow_slug(flow)).mkdir()
    _assert_no_resume_state(flow, tmp_path)


def test_flow_resume_state_unreadable_checkpoints(tmp_path: Path) -> None:
    """A corrupt checkpoints file reports the reason rather than crashing the grid."""
    from ddev.cli.meta.ai.tui.runs import flow_resume_state, flow_slug

    flow = _make_flow()
    run_dir = tmp_path / flow_slug(flow)
    run_dir.mkdir()
    (run_dir / "checkpoints.yaml").write_text("{ not: valid: yaml")

    state = flow_resume_state(flow, runs_dir=tmp_path)
    assert not state.is_resumable
    assert state.error is not None
    assert "checkpoints.yaml" in state.error


def test_flow_resume_state_distinguishes_corrupt_from_clean_slate(tmp_path: Path) -> None:
    """An unreadable checkpoint is not reported as an absent one."""
    from ddev.cli.meta.ai.tui.runs import flow_resume_state, flow_slug

    corrupt = _make_flow(name="Corrupt")
    run_dir = tmp_path / flow_slug(corrupt)
    run_dir.mkdir()
    (run_dir / "checkpoints.yaml").write_text("just a string, not a mapping")

    assert flow_resume_state(corrupt, runs_dir=tmp_path).error is not None
    assert flow_resume_state(_make_flow(name="Never Ran"), runs_dir=tmp_path).error is None


def test_flow_resume_state_failed_checkpoint(tmp_path: Path) -> None:
    """A phase checkpoint with status: failed is resumable (not complete)."""
    from ddev.cli.meta.ai.tui.runs import flow_resume_state, flow_slug

    flow = _make_flow(n_phases=2)
    run_dir = tmp_path / flow_slug(flow)
    run_dir.mkdir()
    # Write a failed checkpoint for the first phase only
    first_phase = flow.flow[0].phase
    (run_dir / "checkpoints.yaml").write_text(
        f"{first_phase}:\n"
        "  status: failed\n"
        "  started_at: '2024-01-01T00:00:00'\n"
        "  finished_at: '2024-01-01T00:01:00'\n"
        "  error: Simulated failure\n"
        "  tokens:\n"
        "    total_input: 0\n"
        "    total_output: 0\n"
    )
    # A failed phase means the run is not successfully complete → resumable
    assert flow_resume_state(flow, runs_dir=tmp_path).is_resumable


# ---------------------------------------------------------------------------
# FlowScreen structure
# ---------------------------------------------------------------------------


async def test_flow_screen_is_togo_screen() -> None:
    """FlowScreen is a TogoScreen subclass."""
    from ddev.cli.meta.ai.tui.screens.base import TogoScreen
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

    assert issubclass(FlowScreen, TogoScreen)


async def test_flow_screen_renders_expected_regions_and_actions() -> None:
    """FlowScreen renders its durable regions and action controls."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PipelineGraph

    flow = _make_flow()
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        pilot.app.screen.query_one("#flow-pipeline", PipelineGraph)
        actions = pilot.app.screen.query_one("#actions", Horizontal)
        button_ids = {button.id for button in actions.query(Button)}
        assert button_ids == {"back", "launch-btn", "resume"}
        assert actions.query_one("#launch-btn", Button).variant == "primary"


async def test_flow_overview_scales_with_wide_viewport() -> None:
    """The overview uses a proportional width on large screens."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

    flow = _make_flow()
    app = _app()
    async with app.run_test(size=(240, 60)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()

        flow_body = pilot.app.screen.query_one("#flow-body")
        overview = pilot.app.screen.query_one("#flow-overview")

        assert overview.region.width >= flow_body.content_region.width * 0.19


async def test_flow_screen_renders_one_phase_node_per_phase() -> None:
    """FlowScreen renders exactly one graph node per phase."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseNode

    flow = _make_flow(n_phases=3)
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        nodes = pilot.app.screen.query(PhaseNode)
        assert len(nodes) == 3


async def test_flow_screen_phase_nodes_show_phase_names() -> None:
    """Each graph node includes the phase ID."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseNode

    flow = _make_flow(n_phases=2)
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        labels = [str(node.render()) for node in pilot.app.screen.query(PhaseNode)]
        assert any("phase_0" in label for label in labels)
        assert any("phase_1" in label for label in labels)


async def test_flow_screen_phase_activation_pushes_config_screen() -> None:
    """Activating a phase node pushes a full-screen phase configuration view."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen
    from ddev.cli.meta.ai.tui.widgets.pipeline_graph import PhaseNode

    flow = _make_flow(n_phases=2)
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        pilot.app.screen.query(PhaseNode).first().action_select()
        await pilot.pause()
        assert isinstance(pilot.app.screen, PhaseConfigScreen)
        assert pilot.app.screen.phase_id == "phase_0"


async def test_phase_config_screen_renders_phase_info_and_agent_details() -> None:
    """PhaseConfigScreen renders phase config, task prompts, and agent details inline."""
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

    flow = _make_flow(n_phases=2)
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.app.push_screen(PhaseConfigScreen(flow, "phase_0"))
        await pilot.pause()
        screen = pilot.app.screen
        screen.query_one("#phase-configuration")
        screen.query_one("#phase-config-grid")
        screen.query_one("#phase-tasks-card")
        screen.query_one("#phase-agent-card")
        assert "phase_0" in str(screen.query_one("#phase-title").render())
        task_prompt = screen.query(".task-prompt").first()
        assert "do something" in task_prompt.source
        assert "agent_a" in str(screen.query_one("#phase-agent-name").render())
        assert "anthropic" in str(screen.query_one("#phase-agent-model").render())
        assert "_No system prompt configured._" in screen.query_one("#phase-agent-prompt").source


async def test_phase_config_description_does_not_reduce_config_at_small_terminal() -> None:
    """A phase description fits the existing summary height and remains scrollable."""
    from textual.containers import VerticalScroll
    from textual.widgets import Static

    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

    flow = _make_flow()
    phase = flow.phases[flow.flow[0].phase]
    app = _app()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(PhaseConfigScreen(flow, phase.name))
        await pilot.pause()
        baseline_grid_height = pilot.app.screen.query_one("#phase-config-grid").region.height
        await pilot.press("escape")
        await pilot.pause()

        phase.description = "\n\n".join(["Explain **this phase** clearly."] * 20)
        await pilot.app.push_screen(PhaseConfigScreen(flow, phase.name))
        await pilot.pause()

        description = pilot.app.screen.query_one("#phase-description", VerticalScroll)
        description_text = description.query_one(Static)
        config_grid = pilot.app.screen.query_one("#phase-config-grid")
        task_title = pilot.app.screen.query_one("CollapsibleTitle")
        footer = pilot.app.screen.query_one("Footer")
        assert description_text.content == phase.description
        assert description.region.height == 2
        assert description.max_scroll_y > 0
        assert config_grid.region.height == baseline_grid_height
        assert task_title.region.bottom <= footer.region.y


async def test_phase_config_screen_renders_resolved_task_prompt() -> None:
    """PhaseConfigScreen renders the prompt already inlined by the engine."""
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

    flow = ResolvedFlow(
        name="Resolved Prompt Flow",
        agents={"agent_a": AgentConfig.model_construct(provider="anthropic", tools=[])},
        phases={
            "review": PhaseConfig(
                name="review",
                agent="agent_a",
                tasks=[TaskConfig(name="inspect", prompt="Read the pull request and summarize the risk.")],
            )
        },
        flow=[FlowEntry(phase="review")],
        variables={},
    )
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.app.push_screen(PhaseConfigScreen(flow, "review"))
        await pilot.pause()

        task_prompt = pilot.app.screen.query(".task-prompt").first()
        assert "Read the pull request" in task_prompt.source
        assert "resolved prompt" in str(pilot.app.screen.query(".task-prompt-source").first().render())


async def test_phase_config_task_prompt_is_scrollable() -> None:
    """Long task prompts are hosted in their own scroll container."""
    from textual.containers import VerticalScroll
    from textual.widgets import Collapsible

    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

    flow = _make_flow()
    phase = flow.phases[flow.flow[0].phase]
    phase.tasks = [
        TaskConfig(name="first", prompt="\n\n".join(["First task prompt."] * 40)),
        TaskConfig(name="second", prompt="\n\n".join(["Second task prompt."] * 40)),
    ]
    app = _app()
    async with app.run_test(size=(200, 60)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(PhaseConfigScreen(flow, flow.flow[0].phase))
        await pilot.pause()

        pilot.app.screen.query_one("#phase-tasks-card", VerticalScroll)
        tasks = list(pilot.app.screen.query(Collapsible))
        titles = list(pilot.app.screen.query("CollapsibleTitle"))
        assert [task.collapsed for task in tasks] == [False, True]
        assert tasks[0].query_one(".task-prompt-scroll", VerticalScroll).max_scroll_y > 0
        assert titles[0].region.right == tasks[0].content_region.right

        await pilot.click("CollapsibleTitle", offset=(titles[0].region.width - 2, 0))
        await pilot.pause()
        assert tasks[0].collapsed is True

        tasks[1].collapsed = False
        await pilot.pause()

        assert [task.collapsed for task in tasks] == [True, False]
        assert tasks[1].query_one(".task-prompt-scroll", VerticalScroll).max_scroll_y > 0


# ---------------------------------------------------------------------------
# Back / escape navigation
# ---------------------------------------------------------------------------


async def test_back_button_pops_to_main() -> None:
    """Pressing Back on FlowScreen returns to MainScreen."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        await pilot.click("#back")
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)


async def test_escape_pops_to_main() -> None:
    """Pressing Escape on FlowScreen returns to MainScreen."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.main import MainScreen

    flow = _make_flow()
    app = _app()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(pilot.app.screen, MainScreen)


# ---------------------------------------------------------------------------
# Resume button visibility
# ---------------------------------------------------------------------------


async def test_resume_button_hidden_with_no_run(tmp_path: Path) -> None:
    """Resume button is not visible when no run dir exists."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

    flow = _make_flow()
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        resume_btn = pilot.app.screen.query_one("#resume", Button)
        assert not resume_btn.display


async def test_resume_button_shown_with_incomplete_run(tmp_path: Path) -> None:
    """Resume button is visible when an incomplete run exists."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

    flow = _make_flow(n_phases=2)
    _write_incomplete_run(tmp_path, flow)
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        resume_btn = pilot.app.screen.query_one("#resume", Button)
        assert resume_btn.display


async def test_resume_button_appears_when_screen_resumes(tmp_path: Path) -> None:
    """A run that fails while the screen is on the stack reveals Resume on return."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

    flow = _make_flow(n_phases=2)
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        flow_screen = pilot.app.screen
        assert not flow_screen.query_one("#resume", Button).display

        await pilot.app.push_screen(PhaseConfigScreen(flow, flow.flow[0].phase))
        await pilot.pause()
        _write_incomplete_run(tmp_path, flow)
        pilot.app.pop_screen()
        await pilot.pause()

        assert pilot.app.screen is flow_screen
        assert flow_screen.query_one("#resume", Button).display


async def test_resume_button_hidden_again_when_run_completes(tmp_path: Path) -> None:
    """A run that finishes while the screen is on the stack hides Resume on return."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

    flow = _make_flow(n_phases=2)
    _write_incomplete_run(tmp_path, flow)
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        flow_screen = pilot.app.screen
        assert flow_screen.query_one("#resume", Button).display

        await pilot.app.push_screen(PhaseConfigScreen(flow, flow.flow[0].phase))
        await pilot.pause()
        _write_complete_run(tmp_path, flow)
        pilot.app.pop_screen()
        await pilot.pause()

        assert not flow_screen.query_one("#resume", Button).display


async def test_phase_config_agent_panel_renders_tools_and_prompt() -> None:
    """PhaseConfigScreen shows agent tools and system prompt inline."""
    from ddev.cli.meta.ai.tui.screens.phase_config import PhaseConfigScreen

    flow = ResolvedFlow(
        name="Agent Detail Flow",
        agents={
            "analyst": AgentConfig.model_construct(
                provider="anthropic",
                model="claude-3-sonnet",
                tools=["read_file", "create_file", "ddev_test"],
                system_prompt="You are the inline analyst.",
            )
        },
        phases={
            "analyse": PhaseConfig(
                name="analyse",
                agent="analyst",
                tasks=[TaskConfig(name="inspect", prompt="inspect this")],
            )
        },
        flow=[FlowEntry(phase="analyse")],
        variables={},
    )
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(PhaseConfigScreen(flow, "analyse"))
        await pilot.pause()

        assert "analyst" in str(pilot.app.screen.query_one("#phase-agent-name").render())
        model = pilot.app.screen.query_one("#phase-agent-model")
        assert "claude-3-sonnet" in str(model.render())
        assert "anthropic" in str(model.render())
        assert model.region.right <= pilot.app.screen.query_one("#phase-agent-card").content_region.right
        rendered_tools = str(pilot.app.screen.query_one("#phase-agent-tools").render())
        assert rendered_tools == "read_file · create_file · ddev_test"
        assert "inline analyst" in pilot.app.screen.query_one("#phase-agent-prompt").source


# ---------------------------------------------------------------------------
# Launch ▶ → LaunchModal → ExecutionScreen
# ---------------------------------------------------------------------------


async def test_launch_button_opens_launch_modal() -> None:
    """Pressing Launch ▶ pushes LaunchModal."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    flow = _make_flow()
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        await pilot.click("#launch-btn")
        await pilot.pause()
        assert isinstance(pilot.app.screen, LaunchModal)


async def test_valid_launch_dismissal_pushes_execution_screen(tmp_path: Path) -> None:
    """After LaunchModal dismisses with values, ExecutionScreen is pushed."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    flow = _make_flow()
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        await pilot.click("#launch-btn")
        await pilot.pause()
        assert isinstance(pilot.app.screen, LaunchModal)
        _provide_prd(pilot.app.screen, tmp_path)
        await pilot.click("#btn-launch")
        await pilot.pause()
        assert isinstance(pilot.app.screen, ExecutionScreen)


async def test_launch_dismissal_passes_runtime_variables_and_timeout(tmp_path: Path) -> None:
    """ExecutionScreen receives runtime_variables from the dismissed LaunchModal."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

    flow = _make_flow()
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow))
        await pilot.pause()
        await pilot.click("#launch-btn")
        await pilot.pause()
        prd = _provide_prd(pilot.app.screen, tmp_path)
        pilot.app.screen.query_one("#input-max_timeout", Input).value = "120"
        await pilot.click("#btn-launch")
        await pilot.pause()
        screen: ExecutionScreen = pilot.app.screen  # type: ignore[assignment]
        assert screen.runtime_variables == {"prd": prd, "max_timeout": "120"}


# ---------------------------------------------------------------------------
# Resume → ExecutionScreen
# ---------------------------------------------------------------------------


async def test_resume_pushes_execution_screen_with_resume_flag(tmp_path: Path) -> None:
    """Resume recollects built-in inputs before pushing ExecutionScreen."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    flow = _make_flow(n_phases=2)
    _write_incomplete_run(tmp_path, flow)
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        await pilot.click("#resume")
        await pilot.pause()

        assert isinstance(pilot.app.screen, LaunchModal)
        _provide_prd(pilot.app.screen, tmp_path)
        await pilot.click("#btn-launch")
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, ExecutionScreen)
        assert screen.resume is True


async def test_resume_refuses_when_run_completes_while_modal_is_open(tmp_path: Path) -> None:
    """The dismiss callback re-checks, so a run finished elsewhere cannot start a doomed resume."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    flow = _make_flow(n_phases=2)
    _write_incomplete_run(tmp_path, flow)
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        flow_screen = pilot.app.screen
        await pilot.click("#resume")
        await pilot.pause()
        assert isinstance(pilot.app.screen, LaunchModal)

        _provide_prd(pilot.app.screen, tmp_path)
        _write_complete_run(tmp_path, flow)
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert not isinstance(pilot.app.screen, ExecutionScreen)
        assert pilot.app.screen is flow_screen
        assert not flow_screen.query_one("#resume", Button).display
        assert "Nothing left to resume" in " ".join(n.message for n in pilot.app._notifications)


async def test_resume_refuses_when_checkpoint_becomes_unreadable_while_modal_is_open(tmp_path: Path) -> None:
    """A checkpoint corrupted mid-flight reports the remedy instead of a wrapped hook error."""
    from ddev.cli.meta.ai.tui.runs import flow_slug
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

    flow = _make_flow(n_phases=2)
    _write_incomplete_run(tmp_path, flow)
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        await pilot.click("#resume")
        await pilot.pause()

        _provide_prd(pilot.app.screen, tmp_path)
        (tmp_path / flow_slug(flow) / "checkpoints.yaml").write_text("{ not: valid: yaml")
        await pilot.click("#btn-launch")
        await pilot.pause()

        assert not isinstance(pilot.app.screen, ExecutionScreen)
        notifications = " ".join(n.message for n in pilot.app._notifications)
        assert "Cannot resume" in notifications
        assert "Delete the checkpoint file" in notifications


async def test_resume_refuses_before_opening_the_modal_when_nothing_to_resume(tmp_path: Path) -> None:
    """A stale Resume button is refused up front rather than after collecting inputs."""
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    flow = _make_flow(n_phases=2)
    _write_incomplete_run(tmp_path, flow)
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        flow_screen = pilot.app.screen
        assert flow_screen.query_one("#resume", Button).display

        _write_complete_run(tmp_path, flow)
        flow_screen._do_resume()
        await pilot.pause()

        assert not isinstance(pilot.app.screen, LaunchModal)
        assert not flow_screen.query_one("#resume", Button).display


async def test_resume_with_inputs_reopens_modal_and_passes_converted_values(tmp_path: Path) -> None:
    """Resume recollects runtime inputs without persisting their contents."""
    from ddev.cli.meta.ai.tui.screens.execution import ExecutionScreen
    from ddev.cli.meta.ai.tui.screens.flow import FlowScreen
    from ddev.cli.meta.ai.tui.screens.launch_modal import LaunchModal

    flow = replace(
        _make_flow(n_phases=2),
        inputs=FlowConfig(
            name="test",
            inputs=[FlowInput(name="token", label="Token", input_type=InputType.STRING, default="fresh-value")],
            flow=[],
        ).inputs,
    )
    _write_incomplete_run(tmp_path, flow)
    app = _app()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await pilot.app.push_screen(FlowScreen(flow, runs_dir=tmp_path))
        await pilot.pause()
        await pilot.click("#resume")
        await pilot.pause()

        assert isinstance(pilot.app.screen, LaunchModal)
        prd = _provide_prd(pilot.app.screen, tmp_path)
        await pilot.click("#btn-launch")
        await pilot.pause()
        screen = pilot.app.screen
        assert isinstance(screen, ExecutionScreen)
        assert screen.resume is True
        assert screen.runtime_variables == {"token": "fresh-value", "prd": prd}
