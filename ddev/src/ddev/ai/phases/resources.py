# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ddev.ai.config.models import AgentConfig
    from ddev.ai.react.factory import ReActProcessFactory
    from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy


class ResourceUnavailableError(Exception):
    """Raised when a phase requests a resource the provider cannot supply."""


class PhaseResources(Protocol):
    """Run-scoped services available to phase builders."""

    def agent_config(self, name: str) -> AgentConfig: ...

    @property
    def file_access_policy(self) -> FileAccessPolicy: ...

    @property
    def process_factory(self) -> ReActProcessFactory: ...
