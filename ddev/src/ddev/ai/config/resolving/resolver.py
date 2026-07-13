# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.ai.config.errors import ConfigStatus, ErrorKind, FlowDiagnostics, FlowError
from ddev.ai.config.registry import BrokenEntry, ResourceKind
from ddev.ai.config.resolving.dependencies import validate_dependencies
from ddev.ai.config.resolving.inlining import build_resolved_flow
from ddev.ai.config.resolving.phases import resolve_scheduled_phases
from ddev.ai.config.resolving.variables import resolve_variables

if TYPE_CHECKING:
    from ddev.ai.config.registry import ResourceRegistry
    from ddev.ai.phases.registry import PhaseRegistryProtocol


class FlowResolver:
    """Cross-resource, flow-scoped validation and inlining over a registry.

    Stateless and per-flow: every :meth:`resolve` call runs the resolving pipeline
    (phases -> dependencies -> variables -> inline) in a single pass, accumulating all
    errors. Knows nothing about files or eager-vs-lazy evaluation.
    """

    def __init__(self, registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol) -> None:
        self._registry = registry
        self._phase_registry = phase_registry

    def resolve(self, flow_name: str) -> FlowDiagnostics:
        """Validate and, if sound, inline one flow into a ``ResolvedFlow``."""
        entry = self._registry.entry(ResourceKind.FLOW, flow_name)
        if entry is None:
            return FlowDiagnostics(
                flow_name,
                ConfigStatus.BROKEN,
                [FlowError(ErrorKind.FLOW, f"Flow {flow_name!r} not found", subject=flow_name)],
            )
        if isinstance(entry, BrokenEntry):
            return FlowDiagnostics(
                flow_name,
                ConfigStatus.BROKEN,
                [
                    FlowError(
                        ErrorKind.FLOW, entry.error or "broken flow", subject=flow_name, sources=[entry.source_file]
                    )
                ],
            )

        flow_config = entry.config
        flow_src = entry.source_file
        scheduled_phases, errors = resolve_scheduled_phases(
            self._registry, self._phase_registry, flow_config, flow_name
        )
        errors.extend(validate_dependencies(flow_config, flow_name, flow_src))
        resolved_variables, var_errors = resolve_variables(self._registry, scheduled_phases, flow_config)
        errors.extend(var_errors)
        if errors:
            return FlowDiagnostics(flow_name, ConfigStatus.BROKEN, errors)

        resolved = build_resolved_flow(self._registry, flow_name, flow_config, scheduled_phases, resolved_variables)
        return FlowDiagnostics(flow_name, ConfigStatus.OK, resolved=resolved)
