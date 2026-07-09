# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ddev.ai.config.models import AgentConfig, FlowConfig, PhaseConfig

ResourceKind = Literal["agent", "phase", "flow", "prompt", "goal", "memory_prompt"]


@dataclass(frozen=True)
class ValidEntry[C]:
    """A resource that parsed and validated, carrying its own identity."""

    kind: ResourceKind
    name: str
    config: C
    source_file: Path


@dataclass(frozen=True)
class BrokenEntry:
    """A resource with a valid, referenceable identity that failed validation."""

    kind: ResourceKind
    name: str
    source_file: Path
    error: str


type Entry[C] = ValidEntry[C] | BrokenEntry


@dataclass(frozen=True)
class ResourceConflict:
    """Two or more entries sharing a (kind, name); every colliding entry is disabled."""

    kind: ResourceKind
    name: str
    sources: list[Path]


class ResourceRegistry:
    """Flat, identity-addressed store of every discovered resource.

    Groups the classified entries by ``(kind, name)``. A key with two or more entries
    is a :class:`ResourceConflict` and is disabled: it is absent from every ok-view and
    ``entry()`` returns ``None`` for it. Holds no reference, variable, or graph knowledge.
    """

    def __init__(self, entries: Iterable[Entry[Any]]) -> None:
        raise NotImplementedError

    def entry(self, kind: ResourceKind, name: str) -> Entry[Any] | None:
        """The single entry for ``(kind, name)``, or ``None`` if absent or conflicting."""
        raise NotImplementedError

    @property
    def agents(self) -> dict[str, AgentConfig]:
        """Valid, non-conflicting agent configs by name."""
        raise NotImplementedError

    @property
    def phases(self) -> dict[str, PhaseConfig]:
        """Valid, non-conflicting phase configs by name."""
        raise NotImplementedError

    @property
    def flows(self) -> dict[str, FlowConfig]:
        """Valid, non-conflicting flow configs by name."""
        raise NotImplementedError

    @property
    def prompts(self) -> dict[str, str]:
        """Valid, non-conflicting prompt bodies by name."""
        raise NotImplementedError

    @property
    def goals(self) -> dict[str, str]:
        """Valid, non-conflicting goal bodies by name."""
        raise NotImplementedError

    @property
    def memories(self) -> dict[str, str]:
        """Valid, non-conflicting memory-prompt bodies by name."""
        raise NotImplementedError

    @property
    def flow_names(self) -> list[str]:
        """Every non-conflicting flow key, valid or broken (for eager diagnostics)."""
        raise NotImplementedError

    @property
    def conflicts(self) -> list[ResourceConflict]:
        raise NotImplementedError

    @property
    def has_conflicts(self) -> bool:
        raise NotImplementedError
