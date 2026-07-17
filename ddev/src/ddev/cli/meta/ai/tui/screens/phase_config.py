# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Full-screen phase configuration view."""

from __future__ import annotations

from collections.abc import Iterator

from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Collapsible, Markdown, Static

from ddev.ai.config.models import AgentConfig, ResolvedFlow, TaskConfig
from ddev.cli.meta.ai.tui.screens.base import TogoScreen


class PhaseConfigScreen(TogoScreen):
    """Shows the full configuration for one phase."""

    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def __init__(self, flow: ResolvedFlow, phase_id: str) -> None:
        super().__init__()
        self.flow = flow
        self.phase_id = phase_id
        self._togo_title = f"{flow.name or 'Flow'} · {phase_id}"

    def compose_body(self) -> Iterator[Widget]:
        phase = self.flow.phases[self.phase_id]
        phase_index = next(index for index, entry in enumerate(self.flow.flow) if entry.phase == self.phase_id)
        dependencies = next(entry.dependencies for entry in self.flow.flow if entry.phase == self.phase_id)

        config_panel = Widget(id="phase-configuration", classes="panel")
        config_panel.border_title = "phase configuration"
        with config_panel:
            with Horizontal(id="phase-summary"):
                with Vertical(id="phase-heading"):
                    yield Static(f"Phase {phase_index:02d}", id="phase-index", classes="eyebrow")
                    yield Static(self.phase_id, id="phase-title")
                with Vertical(id="phase-dependencies-summary"):
                    yield Static("DEPENDENCIES", classes="eyebrow")
                    yield Static(
                        ", ".join(dependencies) if dependencies else "none",
                        id="phase-dependencies",
                        classes="desc",
                    )

            with Horizontal(id="phase-config-grid"):
                tasks_card = VerticalScroll(id="phase-tasks-card", classes="phase-config-card")
                tasks_card.border_title = "tasks"
                with tasks_card:
                    with Vertical(id="phase-tasks"):
                        for index, task in enumerate(phase.tasks):
                            yield from self._compose_task(task, collapsed=index > 0)

                agent_card = Widget(id="phase-agent-card", classes="phase-config-card")
                agent_card.border_title = "agent"
                with agent_card:
                    if phase.agent and phase.agent in self.flow.agents:
                        yield from self._compose_agent(phase.agent, self.flow.agents[phase.agent])
                    else:
                        yield Static("No agent configured for this phase.", classes="desc")

        with Horizontal(id="phase-actions"):
            yield Button("Back", id="back")

    def _compose_task(self, task: TaskConfig, *, collapsed: bool) -> Iterator[Widget]:
        with Collapsible(title=task.name, collapsed=collapsed, classes="phase-task"):
            yield Static("resolved prompt", classes="eyebrow task-prompt-source")
            with VerticalScroll(classes="task-prompt-scroll"):
                yield Markdown(self._resolve_task_prompt(task), classes="task-prompt")

    def _resolve_task_prompt(self, task: TaskConfig) -> str:
        return task.prompt or "_No task prompt configured._"

    def _compose_agent(self, agent_name: str, config: AgentConfig) -> Iterator[Widget]:
        yield Static(agent_name, id="phase-agent-name")
        with Horizontal(id="phase-agent-meta"):
            yield Static(f"provider · {config.provider}", id="phase-agent-provider", classes="badge")
            if config.model:
                yield Static(f"model · {config.model}", id="phase-agent-model", classes="badge")
        yield Static("TOOLS", classes="eyebrow")
        if config.tools:
            yield Static(" · ".join(config.tools), id="phase-agent-tools", classes="tools-box")
        else:
            yield Static("No tools configured", id="phase-agent-tools-empty", classes="desc")
        yield Static("SYSTEM PROMPT", classes="eyebrow")
        yield Markdown(config.system_prompt or "_No system prompt configured._", id="phase-agent-prompt")

    def on_collapsible_expanded(self, event: Collapsible.Expanded) -> None:
        for task in self.query(Collapsible):
            if task is not event.collapsible:
                task.collapsed = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
