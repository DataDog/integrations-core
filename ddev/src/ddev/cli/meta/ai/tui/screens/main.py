# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""MainScreen — lists valid and broken configuration-engine flow results."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from ddev.ai.config.models import ResolvedFlow
from ddev.cli.meta.ai.tui.runs import ai_runs_dir, flow_resume_state
from ddev.cli.meta.ai.tui.screens.base import TogoScreen
from ddev.cli.meta.ai.tui.widgets.flow_card import FlowCard


class MainScreen(TogoScreen):
    """Main dashboard screen listing all available flows."""

    AUTO_FOCUS = "FlowCard"
    TITLE = "Flows"

    @property
    def runs_dir(self) -> Path:
        return ai_runs_dir(self.togo_app.ddev_app.repo.path)

    def compose_body(self) -> Iterator[Widget]:
        results = sorted(self.togo_app.engine.flows.values(), key=lambda result: result.name.casefold())
        yield Static(f"DISCOVERED FLOWS · {len(results)}", classes="eyebrow")
        grid = VerticalScroll(id="flow-grid")
        for i, result in enumerate(results):
            grid.compose_add_child(FlowCard(result=result, index=i, resumable=self._is_resumable(result.resolved)))
        yield grid

    def _is_resumable(self, flow: ResolvedFlow | None) -> bool:
        return flow is not None and flow_resume_state(flow, self.runs_dir).is_resumable

    def on_screen_resume(self) -> None:
        """Re-read resume state whenever this screen becomes active again."""
        for card in self.query(FlowCard):
            card.resumable = self._is_resumable(card.flow)

    def on_flow_card_selected(self, event: FlowCard.Selected) -> None:
        if event.result.resolved is not None:
            from ddev.cli.meta.ai.tui.screens.flow import FlowScreen

            self.app.push_screen(FlowScreen(event.result.resolved, runs_dir=self.runs_dir))
        else:
            from ddev.cli.meta.ai.tui.screens.diagnostics_modal import FlowDiagnosticsModal

            self.app.push_screen(FlowDiagnosticsModal(event.result))
