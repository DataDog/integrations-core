# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.ai.config.errors import ConfigError, ErrorKind, FlowError
from ddev.ai.config.registry import BrokenEntry, ResourceKind

if TYPE_CHECKING:
    from ddev.ai.config.models import FlowConfig, PhaseConfig
    from ddev.ai.config.registry import ResourceRegistry
    from ddev.ai.phases.registry import PhaseRegistryProtocol


def resolve_scheduled_phases(
    registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol, fc: FlowConfig, flow_name: str
) -> tuple[list[PhaseConfig], list[FlowError]]:
    """Resolve each scheduled phase to its config and run its per-phase checks."""
    scheduled_phases: list[PhaseConfig] = []
    errors: list[FlowError] = []
    for fe in fc.flow:
        pc, phase_errors = _resolve_scheduled_phase(registry, fe.phase, flow_name)
        errors.extend(phase_errors)
        if pc is None:
            continue
        scheduled_phases.append(pc)
        errors.extend(_validate_phase(registry, phase_registry, pc))
    return scheduled_phases, errors


def _resolve_scheduled_phase(
    registry: ResourceRegistry, phase_name: str, flow_name: str
) -> tuple[PhaseConfig | None, list[FlowError]]:
    phase_entry = registry.entry(ResourceKind.PHASE, phase_name)
    if phase_entry is None:
        return None, [_unregistered_phase_error(registry, phase_name, flow_name)]
    if isinstance(phase_entry, BrokenEntry):
        return None, [
            FlowError(
                ErrorKind.PHASE,
                f"Phase {phase_name!r} referenced by flow {flow_name!r} is broken: {phase_entry.error}",
                subject=phase_name,
                phase=phase_name,
                sources=[phase_entry.source_file],
            )
        ]
    return phase_entry.config, []


def _unregistered_phase_error(registry: ResourceRegistry, phase_name: str, flow_name: str) -> FlowError:
    conflict = next((c for c in registry.conflicts if c.kind == ResourceKind.PHASE and c.name == phase_name), None)
    if conflict is not None:
        return FlowError(
            ErrorKind.PHASE,
            f"Phase {phase_name!r} referenced by flow {flow_name!r} is defined in multiple sources; "
            "resolve the conflict",
            subject=phase_name,
            phase=phase_name,
            sources=list(conflict.sources),
        )
    flow_entry = registry.entry(ResourceKind.FLOW, flow_name)
    return FlowError(
        ErrorKind.PHASE,
        f"Phase {phase_name!r} referenced by flow {flow_name!r} is not registered",
        subject=phase_name,
        phase=phase_name,
        sources=[flow_entry.source_file],
    )


def _validate_phase(
    registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol, pc: PhaseConfig
) -> list[FlowError]:
    return [
        *_validate_phase_class(registry, phase_registry, pc),
        *_validate_phase_agent(registry, pc),
        *_validate_phase_refs(registry, pc),
    ]


def _validate_phase_class(
    registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol, pc: PhaseConfig
) -> list[FlowError]:
    phase_src = registry.entry(ResourceKind.PHASE, pc.name).source_file
    if not phase_registry.contains(pc.class_):
        return [
            FlowError(
                ErrorKind.PHASE,
                f"Phase {pc.name!r} uses unknown implementation class {pc.class_!r}"
                f"{phase_registry.format_import_errors()}",
                subject=pc.class_,
                phase=pc.name,
                sources=[phase_src],
            )
        ]
    try:
        phase_registry.get(pc.class_).validate_config(pc.name, pc)
    except ConfigError as e:
        return [FlowError(ErrorKind.PHASE, str(e), subject=pc.name, phase=pc.name, sources=[phase_src])]
    except Exception as e:
        return [
            FlowError(
                ErrorKind.PHASE,
                f"Phase {pc.name!r} class {pc.class_!r} raised during validation: {e!r}",
                subject=pc.name,
                phase=pc.name,
                sources=[phase_src],
            )
        ]
    return []


def _validate_phase_agent(registry: ResourceRegistry, pc: PhaseConfig) -> list[FlowError]:
    if pc.agent is None:
        return []
    agent_entry = registry.entry(ResourceKind.AGENT, pc.agent)
    if agent_entry is None:
        phase_src = registry.entry(ResourceKind.PHASE, pc.name).source_file
        return [
            FlowError(
                ErrorKind.AGENT,
                f"Agent {pc.agent!r} referenced by phase {pc.name!r} is not registered",
                subject=pc.agent,
                phase=pc.name,
                sources=[phase_src],
            )
        ]
    if isinstance(agent_entry, BrokenEntry):
        return [
            FlowError(
                ErrorKind.AGENT,
                f"Agent {pc.agent!r} referenced by phase {pc.name!r} is broken: {agent_entry.error}",
                subject=pc.agent,
                phase=pc.name,
                sources=[agent_entry.source_file],
            )
        ]
    return []


def _validate_phase_refs(registry: ResourceRegistry, pc: PhaseConfig) -> list[FlowError]:
    errors: list[FlowError] = []
    for task in pc.tasks:
        if task.prompt_ref is not None:
            errors.extend(_check_ref(registry, ResourceKind.PROMPT, task.prompt_ref, pc.name))
        if task.goal_ref is not None:
            errors.extend(_check_ref(registry, ResourceKind.GOAL, task.goal_ref, pc.name))
    if pc.checkpoint is not None and pc.checkpoint.memory_prompt_ref is not None:
        errors.extend(_check_ref(registry, ResourceKind.MEMORY_PROMPT, pc.checkpoint.memory_prompt_ref, pc.name))
    return errors


def _check_ref(registry: ResourceRegistry, kind: ResourceKind, ref: str, phase_name: str) -> list[FlowError]:
    error_kind = ErrorKind.for_resource(kind)
    ref_entry = registry.entry(kind, ref)
    label = error_kind.value.replace("_", " ").capitalize()
    if ref_entry is None:
        phase_src = registry.entry(ResourceKind.PHASE, phase_name).source_file
        return [
            FlowError(
                error_kind,
                f"{label} {ref!r} referenced by phase {phase_name!r} is not registered",
                subject=ref,
                phase=phase_name,
                sources=[phase_src],
            )
        ]
    if isinstance(ref_entry, BrokenEntry):
        return [
            FlowError(
                error_kind,
                f"{label} {ref!r} referenced by phase {phase_name!r} is broken: {ref_entry.error}",
                subject=ref,
                phase=phase_name,
                sources=[ref_entry.source_file],
            )
        ]
    return []
