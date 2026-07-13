# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Literal, overload

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ddev.ai.config.models import AgentConfig, FlowConfig, PhaseConfig


class ResourceKind(StrEnum):
    AGENT = auto()
    PHASE = auto()
    FLOW = auto()
    PROMPT = auto()
    GOAL = auto()
    MEMORY_PROMPT = auto()


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
        groups: dict[tuple[ResourceKind, str], list[Entry[Any]]] = {}
        for e in entries:
            groups.setdefault((e.kind, e.name), []).append(e)

        self._entries: dict[tuple[ResourceKind, str], Entry[Any]] = {}
        self._conflicts: list[ResourceConflict] = []
        for (kind, name), group in groups.items():
            if len(group) == 1:
                self._entries[(kind, name)] = group[0]
            else:
                self._conflicts.append(ResourceConflict(kind=kind, name=name, sources=[e.source_file for e in group]))

    @overload
    def entry(self, kind: Literal[ResourceKind.AGENT], name: str) -> Entry[AgentConfig] | None: ...
    @overload
    def entry(self, kind: Literal[ResourceKind.PHASE], name: str) -> Entry[PhaseConfig] | None: ...
    @overload
    def entry(self, kind: Literal[ResourceKind.FLOW], name: str) -> Entry[FlowConfig] | None: ...
    @overload
    def entry(
        self, kind: Literal[ResourceKind.PROMPT, ResourceKind.GOAL, ResourceKind.MEMORY_PROMPT], name: str
    ) -> Entry[str] | None: ...

    def entry(self, kind: ResourceKind, name: str) -> Entry[Any] | None:
        """The single entry for ``(kind, name)``, or ``None`` if absent or conflicting."""
        return self._entries.get((kind, name))

    def _valid_configs_of_kind(self, kind: ResourceKind) -> dict[str, Any]:
        """Configs of VALID, non-conflicting entries of ``kind``, keyed by name."""
        return {
            name: entry.config
            for (entry_kind, name), entry in self._entries.items()
            if entry_kind == kind and isinstance(entry, ValidEntry)
        }

    @property
    def agents(self) -> dict[str, AgentConfig]:
        """Valid, non-conflicting agent configs by name."""
        return self._valid_configs_of_kind(ResourceKind.AGENT)

    @property
    def phases(self) -> dict[str, PhaseConfig]:
        """Valid, non-conflicting phase configs by name."""
        return self._valid_configs_of_kind(ResourceKind.PHASE)

    @property
    def flows(self) -> dict[str, FlowConfig]:
        """Valid, non-conflicting flow configs by name."""
        return self._valid_configs_of_kind(ResourceKind.FLOW)

    @property
    def prompts(self) -> dict[str, str]:
        """Valid, non-conflicting prompt bodies by name."""
        return self._valid_configs_of_kind(ResourceKind.PROMPT)

    @property
    def goals(self) -> dict[str, str]:
        """Valid, non-conflicting goal bodies by name."""
        return self._valid_configs_of_kind(ResourceKind.GOAL)

    @property
    def memories(self) -> dict[str, str]:
        """Valid, non-conflicting memory-prompt bodies by name."""
        return self._valid_configs_of_kind(ResourceKind.MEMORY_PROMPT)

    @property
    def flow_names(self) -> list[str]:
        """Every non-conflicting flow key, valid or broken (for eager diagnostics)."""
        return [name for (kind, name) in self._entries if kind == ResourceKind.FLOW]

    @property
    def conflicts(self) -> list[ResourceConflict]:
        return self._conflicts

    @property
    def has_conflicts(self) -> bool:
        return bool(self._conflicts)
