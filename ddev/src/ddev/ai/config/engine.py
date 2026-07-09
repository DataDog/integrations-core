# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging
    from pathlib import Path

    from ddev.ai.config.errors import FlowDiagnostics
    from ddev.ai.config.models import ResolvedFlow
    from ddev.ai.config.registry import ResourceConflict
    from ddev.ai.phases.registry import PhaseRegistryProtocol


class ConfigurationEngine:
    """Thin composition root: wires discovery -> classify -> registry -> resolver.

    Owns the eager pass that validates every discovered flow at construction so callers
    can list all flows and mark the unusable ones. Does not parse, classify, or validate
    directly. Public surface is stable so the future composition root wiring is a drop-in.
    """

    def __init__(
        self,
        core_dir: Path,
        user_dirs: list[str | Path],
        phase_registry: PhaseRegistryProtocol,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        raise NotImplementedError

    def get_flow(self, name: str) -> ResolvedFlow:
        raise NotImplementedError

    @property
    def flows(self) -> dict[str, FlowDiagnostics]:
        raise NotImplementedError

    @property
    def file_errors(self) -> dict[Path, str]:
        raise NotImplementedError

    @property
    def has_conflicts(self) -> bool:
        raise NotImplementedError

    @property
    def conflicts(self) -> list[ResourceConflict]:
        raise NotImplementedError
