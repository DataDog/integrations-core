# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.ai.config.dependency_graph import detect_cycles, topological_sort
from ddev.ai.config.errors import ConfigStatus, ErrorKind, FlowConfigError, FlowDiagnostics, FlowError
from ddev.ai.config.models import ResolvedFlow
from ddev.ai.config.registry import BrokenEntry

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.ai.config.models import FlowConfig, PhaseConfig, TaskConfig
    from ddev.ai.config.registry import ResourceKind, ResourceRegistry
    from ddev.ai.phases.registry import PhaseRegistryProtocol


@dataclass(frozen=True)
class _DeclaredVar:
    name: str
    default: str | None
    origin: str
    source: Path


class FlowResolver:
    """Cross-resource, flow-scoped validation and inlining over a registry.

    Stateless and per-flow: every :meth:`resolve` call validates one flow in a single pass,
    accumulating all errors. Depends on the phase registry only through
    :class:`PhaseRegistryProtocol`. Knows nothing about files or eager-vs-lazy evaluation.
    """

    def __init__(self, registry: ResourceRegistry, phase_registry: PhaseRegistryProtocol) -> None:
        self._registry = registry
        self._phase_registry = phase_registry

    def resolve(self, flow_name: str) -> FlowDiagnostics:
        """Validate and, if sound, inline one flow into a ``ResolvedFlow``."""
        entry = self._registry.entry("flow", flow_name)
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
                        ErrorKind.FLOW,
                        entry.error or "broken flow",
                        subject=flow_name,
                        sources=[entry.source_file],
                    )
                ],
            )

        fc = entry.config
        scheduled_phases, errors = self._validate_scheduled_phases(fc, flow_name)
        errors.extend(self._validate_dependencies(flow_name, fc))
        resolved_variables, var_errors = self._resolve_variables(scheduled_phases, fc)
        errors.extend(var_errors)
        if errors:
            return FlowDiagnostics(flow_name, ConfigStatus.BROKEN, errors)

        resolved = self._build_resolved_flow(flow_name, fc, scheduled_phases, resolved_variables)
        return FlowDiagnostics(flow_name, ConfigStatus.OK, [], resolved=resolved)

    def _validate_scheduled_phases(self, fc: FlowConfig, flow_name: str) -> tuple[list[PhaseConfig], list[FlowError]]:
        scheduled_phases: list[PhaseConfig] = []
        errors: list[FlowError] = []
        for fe in fc.flow:
            pc, phase_errors = self._resolve_scheduled_phase(fe.phase, flow_name)
            errors.extend(phase_errors)
            if pc is None:
                continue
            scheduled_phases.append(pc)
            errors.extend(self._validate_phase(pc))
        return scheduled_phases, errors

    def _resolve_scheduled_phase(self, phase_name: str, flow_name: str) -> tuple[PhaseConfig | None, list[FlowError]]:
        phase_entry = self._registry.entry("phase", phase_name)
        if phase_entry is None:
            return None, [self._unregistered_phase_error(phase_name, flow_name)]
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

    def _unregistered_phase_error(self, phase_name: str, flow_name: str) -> FlowError:
        conflict = next((c for c in self._registry.conflicts if c.kind == "phase" and c.name == phase_name), None)
        if conflict is not None:
            return FlowError(
                ErrorKind.PHASE,
                f"Phase {phase_name!r} referenced by flow {flow_name!r} is defined in multiple sources; "
                "resolve the conflict",
                subject=phase_name,
                phase=phase_name,
                sources=list(conflict.sources),
            )
        flow_entry = self._registry.entry("flow", flow_name)
        return FlowError(
            ErrorKind.PHASE,
            f"Phase {phase_name!r} referenced by flow {flow_name!r} is not registered",
            subject=phase_name,
            phase=phase_name,
            sources=[flow_entry.source_file],
        )

    def _validate_phase(self, pc: PhaseConfig) -> list[FlowError]:
        return [*self._validate_phase_class(pc), *self._validate_phase_agent(pc), *self._validate_phase_refs(pc)]

    def _validate_phase_class(self, pc: PhaseConfig) -> list[FlowError]:
        phase_src = self._registry.entry("phase", pc.name).source_file
        if not self._phase_registry.contains(pc.class_):
            return [
                FlowError(
                    ErrorKind.PHASE,
                    f"Phase {pc.name!r} uses unknown implementation class {pc.class_!r}"
                    f"{self._phase_registry.format_import_errors()}",
                    subject=pc.class_,
                    phase=pc.name,
                    sources=[phase_src],
                )
            ]
        try:
            self._phase_registry.get(pc.class_).validate_config(pc.name, pc)
        except FlowConfigError as e:
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

    def _validate_phase_agent(self, pc: PhaseConfig) -> list[FlowError]:
        if pc.agent is None:
            return []
        agent_entry = self._registry.entry("agent", pc.agent)
        if agent_entry is None:
            phase_src = self._registry.entry("phase", pc.name).source_file
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

    def _validate_phase_refs(self, pc: PhaseConfig) -> list[FlowError]:
        errors: list[FlowError] = []
        for task in pc.tasks:
            if task.prompt_ref is not None:
                errors.extend(self._check_ref("prompt", task.prompt_ref, ErrorKind.PROMPT, pc.name))
            if task.goal_ref is not None:
                errors.extend(self._check_ref("goal", task.goal_ref, ErrorKind.GOAL, pc.name))
        if pc.checkpoint is not None and pc.checkpoint.memory_prompt_ref is not None:
            errors.extend(
                self._check_ref("memory_prompt", pc.checkpoint.memory_prompt_ref, ErrorKind.MEMORY_PROMPT, pc.name)
            )
        return errors

    def _check_ref(self, kind: ResourceKind, ref: str, error_kind: ErrorKind, phase_name: str) -> list[FlowError]:
        ref_entry = self._registry.entry(kind, ref)
        label = error_kind.value.replace("_", " ").capitalize()
        if ref_entry is None:
            phase_src = self._registry.entry("phase", phase_name).source_file
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

    def _validate_dependencies(self, flow_name: str, fc: FlowConfig) -> list[FlowError]:
        flow_src = self._registry.entry("flow", flow_name).source_file
        dependency_map = {fe.phase: fe.dependencies for fe in fc.flow}
        return [
            *self._check_duplicate_schedule(fc, flow_name, flow_src),
            *self._check_unscheduled_dependencies(fc, flow_name, dependency_map, flow_src),
            *self._check_dependency_cycles(flow_name, dependency_map, flow_src),
        ]

    def _check_duplicate_schedule(self, fc: FlowConfig, flow_name: str, flow_src: Path) -> list[FlowError]:
        seen: set[str] = set()
        errors: list[FlowError] = []
        for fe in fc.flow:
            if fe.phase in seen:
                errors.append(
                    FlowError(
                        ErrorKind.DEPENDENCY,
                        f"Phase {fe.phase!r} is scheduled more than once in flow {flow_name!r}",
                        subject=fe.phase,
                        phase=fe.phase,
                        sources=[flow_src],
                    )
                )
            seen.add(fe.phase)
        return errors

    def _check_unscheduled_dependencies(
        self, fc: FlowConfig, flow_name: str, dependency_map: dict[str, list[str]], flow_src: Path
    ) -> list[FlowError]:
        errors: list[FlowError] = []
        for fe in fc.flow:
            for dep in fe.dependencies:
                if dep not in dependency_map:
                    errors.append(
                        FlowError(
                            ErrorKind.DEPENDENCY,
                            f"Phase {fe.phase!r} depends on {dep!r}, which is not scheduled in flow {flow_name!r}",
                            subject=dep,
                            phase=fe.phase,
                            sources=[flow_src],
                        )
                    )
        return errors

    def _check_dependency_cycles(
        self, flow_name: str, dependency_map: dict[str, list[str]], flow_src: Path
    ) -> list[FlowError]:
        cycles, truncated = detect_cycles(dependency_map)
        errors = [
            FlowError(
                ErrorKind.DEPENDENCY,
                f"Dependency cycle detected in flow {flow_name!r}: {' -> '.join(cycle)}",
                sources=[flow_src],
            )
            for cycle in cycles
        ]
        if truncated:
            errors.append(
                FlowError(
                    ErrorKind.DEPENDENCY,
                    f"Cycle detection truncated in flow {flow_name!r} (too many cycles)",
                    sources=[flow_src],
                )
            )
        return errors

    def _resolve_variables(
        self, scheduled_phases: list[PhaseConfig], fc: FlowConfig
    ) -> tuple[dict[str, str], list[FlowError]]:
        declared = self._gather_variable_declarations(scheduled_phases)
        defaults, errors = self._collect_default_values(declared)
        errors.extend(self._find_missing_variables(declared, fc))
        resolved = {**defaults, **fc.variables}
        return resolved, errors

    def _gather_variable_declarations(self, scheduled_phases: list[PhaseConfig]) -> list[_DeclaredVar]:
        declared: list[_DeclaredVar] = []
        for pc in scheduled_phases:
            phase_src = self._registry.entry("phase", pc.name).source_file
            if pc.agent is not None and pc.agent in self._registry.agents:
                agent_src = self._registry.entry("agent", pc.agent).source_file
                for v in self._registry.agents[pc.agent].variables:
                    declared.append(_DeclaredVar(v.name, v.default, f"agent {pc.agent!r}", agent_src))
            for v in pc.variables:
                declared.append(_DeclaredVar(v.name, v.default, f"phase {pc.name!r}", phase_src))
        return declared

    def _collect_default_values(self, declared: list[_DeclaredVar]) -> tuple[dict[str, str], list[FlowError]]:
        by_name: dict[str, list[_DeclaredVar]] = {}
        for dv in declared:
            by_name.setdefault(dv.name, []).append(dv)

        defaults: dict[str, str] = {}
        errors: list[FlowError] = []
        for name, entries in by_name.items():
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

    def _find_missing_variables(self, declared: list[_DeclaredVar], fc: FlowConfig) -> list[FlowError]:
        by_name: dict[str, list[_DeclaredVar]] = {}
        for dv in declared:
            by_name.setdefault(dv.name, []).append(dv)

        errors: list[FlowError] = []
        for name, entries in by_name.items():
            if name in fc.variables:
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
                    f"Required variable {name!r} has no default and is not supplied by the flow "
                    f"(declared in {origins})",
                    subject=name,
                    sources=sources,
                )
            )
        return errors

    def _build_resolved_flow(
        self,
        flow_name: str,
        fc: FlowConfig,
        scheduled_phases: list[PhaseConfig],
        resolved_variables: dict[str, str],
    ) -> ResolvedFlow:
        return ResolvedFlow(
            name=flow_name,
            agents={pc.agent: self._registry.agents[pc.agent] for pc in scheduled_phases if pc.agent is not None},
            phases={pc.name: self._inline_phase(pc) for pc in scheduled_phases},
            flow=topological_sort(fc.flow),
            variables=resolved_variables,
        )

    def _inline_phase(self, phase: PhaseConfig) -> PhaseConfig:
        tasks = [self._inline_task(task) for task in phase.tasks]
        checkpoint = phase.checkpoint
        if checkpoint is not None and checkpoint.memory_prompt_ref is not None:
            checkpoint = checkpoint.model_copy(
                update={
                    "memory_prompt": self._registry.memories[checkpoint.memory_prompt_ref],
                    "memory_prompt_ref": None,
                }
            )
        return phase.model_copy(update={"tasks": tasks, "checkpoint": checkpoint})

    def _inline_task(self, task: TaskConfig) -> TaskConfig:
        update: dict[str, str | None] = {}
        if task.prompt_ref is not None:
            update["prompt"] = self._registry.prompts[task.prompt_ref]
            update["prompt_ref"] = None
        if task.goal_ref is not None:
            update["goal"] = self._registry.goals[task.goal_ref]
            update["goal_ref"] = None
        return task.model_copy(update=update) if update else task
