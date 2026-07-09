# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.ai.config.errors import FlowDiagnostics
    from ddev.ai.config.registry import ResourceRegistry
    from ddev.ai.phases.registry import PhaseRegistryProtocol


class FlowResolver:
    """Cross-resource, flow-scoped validation and inlining over a registry.

    Stateless and per-flow: every :meth:`resolve` call validates one flow in a single pass,
    accumulating all errors. Depends on the phase registry only through
    :class:`PhaseRegistryProtocol`. Knows nothing about files or eager-vs-lazy evaluation.
    """

    def __init__(self, registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol) -> None:
        raise NotImplementedError

    def resolve(self, flow_name: str) -> FlowDiagnostics:
        """Validate and, if sound, inline one flow into a ``ResolvedFlow``."""
        raise NotImplementedError
