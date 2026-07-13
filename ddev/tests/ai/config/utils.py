# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config.models import AgentConfig

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.ai.config.models import PhaseConfig
    from ddev.ai.phases.base import Phase


def make_provider_registry(*names: str) -> AgentProviderRegistry:
    registry = AgentProviderRegistry()
    for name in names:
        registry.register(name, MagicMock())
    return registry


def make_agent_config(**kwargs: Any) -> AgentConfig:
    provider = kwargs.get("provider", "anthropic")
    registry = make_provider_registry(provider)
    return AgentConfig.model_validate(kwargs, context={"provider_registry": registry})


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class NoopPhase:
    @classmethod
    def validate_config(cls, phase_id: str, config: PhaseConfig) -> None:
        return None


class StubReg:
    """A PhaseRegistryProtocol stub that accepts every phase class."""

    def __init__(self, import_errors: dict[str, str] | None = None) -> None:
        self.import_errors = import_errors or {}

    def contains(self, name: str) -> bool:
        return True

    def get(self, name: str) -> type[Phase]:
        return NoopPhase  # type: ignore[return-value]

    def format_import_errors(self) -> str:
        return "".join(f"\n{module}: {msg}" for module, msg in self.import_errors.items())


class StubRegMissing:
    """A PhaseRegistryProtocol stub whose ``missing`` names are treated as unregistered."""

    def __init__(self, missing: set[str]) -> None:
        self._missing = missing
        self.import_errors: dict[str, str] = {}

    def contains(self, name: str) -> bool:
        return name not in self._missing

    def get(self, name: str) -> type[Phase]:
        return NoopPhase  # type: ignore[return-value]

    def format_import_errors(self) -> str:
        return ""
