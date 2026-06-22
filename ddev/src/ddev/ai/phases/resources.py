# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ddev.ai.phases.config import AgentConfig
    from ddev.ai.react.factory import ReActProcessFactory


class ResourceUnavailableError(Exception):
    """Raised when a phase requests a resource the provider cannot supply."""


class PhaseResources(Protocol):
    """Run-scoped services available to phase builders."""

    def agent_config(self, name: str) -> AgentConfig: ...

    @property
    def process_factory(self) -> ReActProcessFactory: ...
