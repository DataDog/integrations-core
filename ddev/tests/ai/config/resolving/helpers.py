# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ddev.ai.config.models import AgentConfig, FlowConfig, PhaseConfig
from ddev.ai.config.registry import ResourceKind, ValidEntry

if TYPE_CHECKING:
    from ddev.ai.config.models import FlowEntry


def agent_entry(name: str, path: str = "/x/agent.md", **kwargs) -> ValidEntry:
    return ValidEntry(kind=ResourceKind.AGENT, name=name, config=AgentConfig(**kwargs), source_file=Path(path))


def phase_entry(name: str, path: str | None = None, **kwargs) -> ValidEntry:
    source_file = Path(path or f"/x/{name}.yaml")
    return ValidEntry(
        kind=ResourceKind.PHASE, name=name, config=PhaseConfig(name=name, **kwargs), source_file=source_file
    )


def flow_entry(name: str, entries: list[FlowEntry], path: str = "/x/flow.yaml", **kwargs) -> ValidEntry:
    config = FlowConfig(name=name, flow=entries, **kwargs)
    return ValidEntry(kind=ResourceKind.FLOW, name=name, config=config, source_file=Path(path))


def prompt_entry(name: str, body: str, path: str | None = None) -> ValidEntry:
    return ValidEntry(kind=ResourceKind.PROMPT, name=name, config=body, source_file=Path(path or f"/x/{name}.md"))


def goal_entry(name: str, body: str, path: str | None = None) -> ValidEntry:
    return ValidEntry(kind=ResourceKind.GOAL, name=name, config=body, source_file=Path(path or f"/x/{name}.md"))


def memory_entry(name: str, body: str, path: str | None = None) -> ValidEntry:
    return ValidEntry(
        kind=ResourceKind.MEMORY_PROMPT, name=name, config=body, source_file=Path(path or f"/x/{name}.md")
    )


class RaisingPhase:
    @classmethod
    def validate_config(cls, phase_id, config):
        raise ValueError("boom")


class StubRegRaising:
    def contains(self, n):
        return True

    def get(self, n):
        return RaisingPhase

    def format_import_errors(self):
        return ""
