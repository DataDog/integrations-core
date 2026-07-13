# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ddev.ai.config.classify import classify
from ddev.ai.config.errors import ConfigError, ErrorKind, FlowError
from ddev.ai.config.loading.discovery import discover
from ddev.ai.config.loading.files import FileError
from ddev.ai.config.models import ConfigStatus, FlowResult
from ddev.ai.config.registry import ResourceKind, ResourceRegistry
from ddev.ai.config.resolving.resolver import FlowResolver

if TYPE_CHECKING:
    from ddev.ai.config.models import ResolvedFlow
    from ddev.ai.config.registry import Entry, ResourceConflict
    from ddev.ai.phases.registry import PhaseRegistryProtocol


class ConfigurationEngine:
    """Thin composition root: wires discovery -> classify -> registry -> resolver.

    Owns the eager pass that validates every discovered flow at construction so callers
    can list all flows and mark the unusable ones. Does not parse, classify, or validate
    directly.
    """

    def __init__(
        self,
        core_dir: Path,
        user_dirs: list[str | Path],
        phase_registry: PhaseRegistryProtocol,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)

        if not core_dir.is_dir():
            raise ConfigError(f"Core config directory does not exist or is not a directory: {core_dir}")
        resolved_dirs = [core_dir, *self._resolve_user_dirs(user_dirs)]

        entries: list[Entry[Any]] = []
        self._file_errors: dict[Path, str] = {}
        for loaded in discover(resolved_dirs):
            if isinstance(loaded, FileError):
                self._record_file_error(loaded.path, loaded.message)
                continue
            output = classify(loaded)
            entries.extend(output.entries)
            for file_error in output.file_errors:
                self._record_file_error(file_error.path, file_error.message)

        self._registry = ResourceRegistry(entries)
        resolver = FlowResolver(self._registry, phase_registry)
        self._flow_results = {name: resolver.resolve(name) for name in self._registry.flow_names}
        self._add_flow_conflict_results()

    def _resolve_user_dirs(self, user_dirs: list[str | Path]) -> list[Path]:
        resolved = []
        for d in user_dirs:
            p = Path(d).expanduser().resolve()
            if not p.is_dir():
                raise ConfigError(f"User config directory does not exist or is not a directory: {p}")
            resolved.append(p)
        return resolved

    def _add_flow_conflict_results(self) -> None:
        """Surface flow-kind conflicts (disabled in the registry) as broken flows."""
        for conflict in self._registry.conflicts:
            if conflict.kind != ResourceKind.FLOW or conflict.name in self._flow_results:
                continue
            sources = ", ".join(str(s) for s in conflict.sources)
            self._flow_results[conflict.name] = FlowResult(
                conflict.name,
                ConfigStatus.BROKEN,
                [
                    FlowError(
                        ErrorKind.FLOW,
                        f"Flow {conflict.name!r} has conflicting definitions: {sources}",
                        subject=conflict.name,
                        sources=list(conflict.sources),
                    )
                ],
            )

    def _record_file_error(self, path: Path, message: str) -> None:
        existing = self._file_errors.get(path)
        self._file_errors[path] = f"{existing}; {message}" if existing else message
        self._logger.warning("Skipping unparseable config in %s: %s", path, message)

    def _file_errors_note(self) -> str:
        if not self._file_errors:
            return ""
        listed = "\n".join(f"  {p}: {msg}" for p, msg in self._file_errors.items())
        return f"\nNote: these files failed to parse and may contain the missing resource:\n{listed}"

    def get_flow(self, name: str) -> ResolvedFlow:
        result = self._flow_results.get(name)
        if result is None:
            raise ConfigError(f"Flow {name!r} not found{self._file_errors_note()}")
        if result.status is ConfigStatus.BROKEN:
            raise ConfigError(f"Flow {name!r} is invalid:\n" + "\n".join(f"  {e.message}" for e in result.errors))
        if result.resolved is None:
            raise ConfigError(f"Flow {name!r} passed validation but produced no resolved flow (engine bug)")
        return result.resolved

    @property
    def flows(self) -> dict[str, FlowResult]:
        return self._flow_results

    @property
    def file_errors(self) -> dict[Path, str]:
        return dict(self._file_errors)

    @property
    def has_conflicts(self) -> bool:
        return self._registry.has_conflicts

    @property
    def conflicts(self) -> list[ResourceConflict]:
        return self._registry.conflicts
