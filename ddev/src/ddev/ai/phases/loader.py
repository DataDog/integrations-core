# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import logging
import sys
from pathlib import Path

from ddev.ai.config.engine import CORE_PHASES_DIR
from ddev.ai.config.errors import FlowConfigError
from ddev.ai.config.models import ResolvedFlow
from ddev.ai.phases.registry import PhaseRegistry, discover_and_register_phases


def _import_prefix_from_path(path: Path) -> str:
    """Derive the dotted import prefix for path from sys.path entries."""
    resolved = path.resolve()
    for entry in sys.path:
        if not entry:
            continue
        root = Path(entry).resolve()
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            continue
        return ".".join(rel.parts)
    raise RuntimeError(f"Could not derive import prefix for {path}")


class PhaseLoader:
    """Discovers phase classes from CORE_PHASES_DIR and user dirs, validates against a resolved flow."""

    def __init__(
        self,
        user_dirs: list[Path] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._user_dirs = user_dirs or []
        self._logger = logger or logging.getLogger(__name__)

    def load(self, resolved: ResolvedFlow) -> PhaseRegistry:
        """Discover all phase classes, validate against resolved flow, return populated registry."""
        registry = PhaseRegistry()
        self._discover(registry)
        self._validate(registry, resolved)
        return registry

    def _phase_dirs(self) -> list[Path]:
        extra = [d for user_dir in self._user_dirs for d in user_dir.rglob("phases") if d.is_dir()]
        return [CORE_PHASES_DIR, *extra]

    def _discover(self, registry: PhaseRegistry) -> None:
        seen: set[Path] = set()
        for phases_dir in self._phase_dirs():
            if not phases_dir.is_dir():
                continue
            resolved_path = phases_dir.resolve()
            if resolved_path in seen:
                continue
            seen.add(resolved_path)
            try:
                prefix = _import_prefix_from_path(phases_dir)
            except RuntimeError:
                self._logger.warning(
                    "phases/ directory %s is not under any sys.path entry — "
                    "its phase classes cannot be auto-imported and will be unavailable at runtime",
                    phases_dir,
                )
                continue
            discover_and_register_phases(registry, phases_dir, prefix)

    def _validate(self, registry: PhaseRegistry, resolved: ResolvedFlow) -> None:
        for phase_id, phase_config in resolved.phases.items():
            try:
                phase_cls = registry.get(phase_config.class_)
            except ValueError as e:
                raise FlowConfigError(
                    f"Phase {phase_id!r} declares unknown class {phase_config.class_!r}: {e}"
                ) from e
            phase_cls.validate_config(phase_id, phase_config, resolved.agents)
