# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.ai.config.errors import ErrorKind, FlowError
from ddev.ai.config.registry import ResourceKind

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.ai.config.models import FlowConfig, PhaseConfig
    from ddev.ai.config.registry import ResourceRegistry


READ_FILE_TOOL = "read_file"


@dataclass(frozen=True)
class DeclaredVar:
    name: str
    default: str | None
    origin: str
    source: Path


def resolve_variables(
    registry: ResourceRegistry, scheduled_phases: list[PhaseConfig], flow_config: FlowConfig
) -> tuple[dict[str, str], list[FlowError]]:
    """Gather variable declarations, resolve defaults, and apply ``flow > default``."""
    declared = _gather_variable_declarations(registry, scheduled_phases)
    guaranteed_inputs = {
        flow_input.name for flow_input in flow_config.inputs if flow_input.required or flow_input.default is not None
    }
    supplied = set(flow_config.variables) | guaranteed_inputs
    defaults, errors = _collect_default_values(declared, supplied=supplied)
    errors.extend(_find_missing_variables(declared, supplied))
    resolved = {**defaults, **flow_config.variables}
    return resolved, errors


def validate_snapshot_readers(
    registry: ResourceRegistry, scheduled_phases: list[PhaseConfig], flow_config: FlowConfig
) -> list[FlowError]:
    """Ensure agents given a snapshot input can open the file it points at.

    Snapshot inputs are delivered as a path, so an agent without a read tool would
    silently receive a location it cannot open instead of failing outright.
    """
    snapshot_inputs = {flow_input.name for flow_input in flow_config.inputs if flow_input.snapshot}
    if not snapshot_inputs:
        return []

    errors: list[FlowError] = []
    for phase_config in scheduled_phases:
        agent_name = phase_config.agent
        agent = registry.agents.get(agent_name) if agent_name is not None else None
        if agent is None or READ_FILE_TOOL in agent.tools:
            continue
        declared = {v.name for v in phase_config.variables} | {v.name for v in agent.variables}
        consumed = sorted(snapshot_inputs & declared)
        if not consumed:
            continue
        names = ", ".join(repr(name) for name in consumed)
        errors.append(
            FlowError(
                ErrorKind.AGENT,
                f"Agent {agent_name!r} uses snapshot input(s) {names}, which are supplied as a file path, "
                f"but does not declare the {READ_FILE_TOOL!r} tool",
                subject=agent_name,
                phase=phase_config.name,
                sources=[registry.entry(ResourceKind.AGENT, agent_name).source_file],
            )
        )
    return errors


def _gather_variable_declarations(registry: ResourceRegistry, scheduled_phases: list[PhaseConfig]) -> list[DeclaredVar]:
    declared: list[DeclaredVar] = []
    for phase_config in scheduled_phases:
        phase_src = registry.entry(ResourceKind.PHASE, phase_config.name).source_file
        if phase_config.agent is not None and phase_config.agent in registry.agents:
            agent_src = registry.entry(ResourceKind.AGENT, phase_config.agent).source_file
            for v in registry.agents[phase_config.agent].variables:
                declared.append(DeclaredVar(v.name, v.default, f"agent {phase_config.agent!r}", agent_src))
        for v in phase_config.variables:
            declared.append(DeclaredVar(v.name, v.default, f"phase {phase_config.name!r}", phase_src))
    return declared


def _collect_default_values(declared: list[DeclaredVar], supplied: set[str]) -> tuple[dict[str, str], list[FlowError]]:
    """Resolve each variable's default; a value the flow supplies explicitly resolves any conflict."""
    by_name: dict[str, list[DeclaredVar]] = {}
    for dv in declared:
        by_name.setdefault(dv.name, []).append(dv)

    defaults: dict[str, str] = {}
    errors: list[FlowError] = []
    for name, entries in by_name.items():
        if name in supplied:
            continue
        with_default = [dv for dv in entries if dv.default is not None]
        distinct_values = {dv.default for dv in entries if dv.default is not None}
        if len(distinct_values) > 1:
            origins = ", ".join(f"{dv.default!r} from {dv.origin}" for dv in with_default)
            sources: list[Path] = []
            for dv in with_default:
                if dv.source not in sources:
                    sources.append(dv.source)
            errors.append(
                FlowError(
                    ErrorKind.VARIABLE,
                    f"Variable {name!r} has conflicting defaults: {origins}; "
                    "declare a single default or supply the variable explicitly",
                    subject=name,
                    sources=sources,
                )
            )
        elif distinct_values:
            defaults[name] = next(iter(distinct_values))
    return defaults, errors


def _find_missing_variables(declared: list[DeclaredVar], supplied: set[str]) -> list[FlowError]:
    by_name: dict[str, list[DeclaredVar]] = {}
    for dv in declared:
        by_name.setdefault(dv.name, []).append(dv)

    errors: list[FlowError] = []
    for name, entries in by_name.items():
        if name in supplied:
            continue
        if any(dv.default is not None for dv in entries):
            continue
        origins = ", ".join(dv.origin for dv in entries)
        sources: list[Path] = []
        for dv in entries:
            if dv.source not in sources:
                sources.append(dv.source)
        errors.append(
            FlowError(
                ErrorKind.VARIABLE,
                f"Required variable {name!r} has no default and is not supplied by the flow (declared in {origins})",
                subject=name,
                sources=sources,
            )
        )
    return errors
