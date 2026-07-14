# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ddev.ai.config.errors import ConfigError, ErrorKind, FlowError
from ddev.ai.config.registry import BrokenEntry, ResourceConflict, ResourceKind

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.ai.config.models import FlowConfig, PhaseConfig
    from ddev.ai.config.registry import ResourceRegistry, ValidEntry
    from ddev.ai.phases.registry import PhaseRegistryProtocol


def resolve_scheduled_phases(
    registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol, flow_config: FlowConfig, flow_name: str
) -> tuple[list[PhaseConfig], list[FlowError]]:
    """Resolve each scheduled phase to its config and run its per-phase checks."""
    scheduled_phases: list[PhaseConfig] = []
    errors: list[FlowError] = []
    for step in flow_config.flow:
        phase_config, phase_errors = _resolve_scheduled_phase(registry, step.phase, flow_name)
        errors.extend(phase_errors)
        if phase_config is None:
            continue
        scheduled_phases.append(phase_config)
        errors.extend(_validate_phase(registry, phase_registry, phase_config))
    return scheduled_phases, errors


def _resolve_scheduled_phase(
    registry: ResourceRegistry, phase_name: str, flow_name: str
) -> tuple[PhaseConfig | None, list[FlowError]]:
    flow_source = registry.entry(ResourceKind.FLOW, flow_name).source_file
    phase_entry, errors = _resolve_resource_reference(
        registry,
        ResourceKind.PHASE,
        phase_name,
        referenced_by=f"flow {flow_name!r}",
        reference_source=flow_source,
        phase_name=phase_name,
    )
    if phase_entry is None:
        return None, errors
    return phase_entry.config, []


def _resolve_resource_reference(
    registry: ResourceRegistry,
    kind: ResourceKind,
    name: str,
    *,
    referenced_by: str,
    reference_source: Path,
    phase_name: str | None = None,
) -> tuple[ValidEntry[Any] | None, list[FlowError]]:
    """Resolve a reference to a resource, mapping every non-valid state to its own diagnostic."""
    result = registry.lookup(kind, name)
    error_kind = ErrorKind.for_resource(kind)
    label = kind.value.replace("_", " ").capitalize()

    def error(reason: str, sources: list[Path]) -> tuple[None, list[FlowError]]:
        message = f"{label} {name!r} referenced by {referenced_by} {reason}"
        return None, [FlowError(error_kind, message, subject=name, phase=phase_name, sources=sources)]

    if result is None:
        return error("is not registered", [reference_source])
    if isinstance(result, ResourceConflict):
        return error("has conflicting definitions", list(result.sources))
    if isinstance(result, BrokenEntry):
        return error(f"is broken: {result.error}", [result.source_file])
    return result, []


def _validate_phase(
    registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol, phase_config: PhaseConfig
) -> list[FlowError]:
    return [
        *_validate_phase_class(registry, phase_registry, phase_config),
        *_validate_phase_agent(registry, phase_config),
        *_validate_phase_refs(registry, phase_config),
    ]


def _validate_phase_class(
    registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol, phase_config: PhaseConfig
) -> list[FlowError]:
    phase_src = registry.entry(ResourceKind.PHASE, phase_config.name).source_file
    if not phase_registry.contains(phase_config.class_):
        return [
            FlowError(
                ErrorKind.PHASE,
                f"Phase {phase_config.name!r} uses unknown implementation class {phase_config.class_!r}"
                f"{phase_registry.format_import_errors()}",
                subject=phase_config.class_,
                phase=phase_config.name,
                sources=[phase_src],
            )
        ]
    try:
        phase_registry.get(phase_config.class_).validate_config(phase_config.name, phase_config)
    except ConfigError as e:
        return [
            FlowError(ErrorKind.PHASE, str(e), subject=phase_config.name, phase=phase_config.name, sources=[phase_src])
        ]
    except Exception as e:
        return [
            FlowError(
                ErrorKind.PHASE,
                f"Phase {phase_config.name!r} class {phase_config.class_!r} raised during validation: {e!r}",
                subject=phase_config.name,
                phase=phase_config.name,
                sources=[phase_src],
            )
        ]
    return []


def _validate_phase_agent(registry: ResourceRegistry, phase_config: PhaseConfig) -> list[FlowError]:
    if phase_config.agent is None:
        return []
    phase_src = registry.entry(ResourceKind.PHASE, phase_config.name).source_file
    _, errors = _resolve_resource_reference(
        registry,
        ResourceKind.AGENT,
        phase_config.agent,
        referenced_by=f"phase {phase_config.name!r}",
        reference_source=phase_src,
        phase_name=phase_config.name,
    )
    return errors


def _validate_phase_refs(registry: ResourceRegistry, phase_config: PhaseConfig) -> list[FlowError]:
    errors: list[FlowError] = []
    for task in phase_config.tasks:
        if task.prompt_ref is not None:
            errors.extend(_check_ref(registry, ResourceKind.PROMPT, task.prompt_ref, phase_config.name))
        if task.goal_ref is not None:
            errors.extend(_check_ref(registry, ResourceKind.GOAL, task.goal_ref, phase_config.name))
    if phase_config.checkpoint is not None and phase_config.checkpoint.memory_prompt_ref is not None:
        errors.extend(
            _check_ref(
                registry, ResourceKind.MEMORY_PROMPT, phase_config.checkpoint.memory_prompt_ref, phase_config.name
            )
        )
    return errors


def _check_ref(registry: ResourceRegistry, kind: ResourceKind, ref: str, phase_name: str) -> list[FlowError]:
    phase_src = registry.entry(ResourceKind.PHASE, phase_name).source_file
    _, errors = _resolve_resource_reference(
        registry,
        kind,
        ref,
        referenced_by=f"phase {phase_name!r}",
        reference_source=phase_src,
        phase_name=phase_name,
    )
    return errors
