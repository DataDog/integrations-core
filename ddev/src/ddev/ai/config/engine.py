# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import TypeAdapter, ValidationError

from ddev.ai.config.errors import FlowConfigError, detect_cycles
from ddev.ai.config.md import parse_md_file
from ddev.ai.config.models import (
    AgentConfig,
    FlowConfig,
    FlowEnvelope,
    PhaseConfig,
    PhaseEnvelope,
    ResolvedFlow,
    ResourceEnvelope,
)

if TYPE_CHECKING:
    from ddev.ai.phases.registry import PhaseRegistry

ResourceKind = Literal["agent", "phase", "flow", "prompt", "goal", "memory_prompt"]


class ConfigStatus(StrEnum):
    OK = "ok"
    BROKEN = "broken"


class ErrorKind(StrEnum):
    FLOW = "flow"
    PHASE = "phase"
    AGENT = "agent"
    PROMPT = "prompt"
    GOAL = "goal"
    MEMORY_PROMPT = "memory_prompt"
    DEPENDENCY = "dependency"
    VARIABLE = "variable"


@dataclass
class ValidEntry[C]:
    config: C
    source_file: Path


@dataclass
class BrokenEntry:
    source_file: Path
    error: str


type RegistryEntry[C] = ValidEntry[C] | BrokenEntry


@dataclass
class ConfigConflict:
    name: str
    type: ResourceKind
    sources: list[Path]


@dataclass(frozen=True)
class _DeclaredVar:
    name: str
    default: str | None
    origin: str  # name of the resource that declared the variable e.g. "agent 'writer'
    source: Path  # the declaring file, for FlowError.sources


@dataclass(frozen=True)
class FlowError:
    kind: ErrorKind
    message: str
    subject: str | None = None  # the named entity the error is about (phase/agent/ref/variable name)
    phase: str | None = None  # the phase context, when the error occurs inside one
    sources: list[Path] = field(default_factory=list)  # every file relevant to fixing it


@dataclass
class FlowDiagnostics:
    name: str
    status: ConfigStatus
    errors: list[FlowError]
    resolved: ResolvedFlow | None = None


RESOURCE_ADAPTER: TypeAdapter[PhaseEnvelope | FlowEnvelope] = TypeAdapter(ResourceEnvelope)

PROMPT_TYPES = {"prompt", "goal", "memory_prompt"}


class ConfigurationEngine:
    def __init__(
        self,
        core_dir: Path,
        user_dirs: list[str | Path],
        phase_registry: PhaseRegistry,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._phase_registry = phase_registry

        resolved_user_dirs = self._resolve_user_dirs(user_dirs)

        if not core_dir.is_dir():
            raise FlowConfigError(f"Core config directory does not exist or is not a directory: {core_dir}")

        self._agents: dict[str, RegistryEntry[AgentConfig]] = {}
        self._phases: dict[str, RegistryEntry[PhaseConfig]] = {}
        self._flows: dict[str, RegistryEntry[FlowConfig]] = {}
        self._prompts: dict[str, RegistryEntry[str]] = {}
        self._goals: dict[str, RegistryEntry[str]] = {}
        self._memories: dict[str, RegistryEntry[str]] = {}

        self._conflicts: list[ConfigConflict] = []
        self._file_errors: dict[Path, str] = {}
        self._pending: dict[tuple[ResourceKind, str], list[RegistryEntry[Any]]] = {}

        for base_dir in [core_dir, *resolved_user_dirs]:
            self._scan_dir(base_dir)

        self._resolve_pending()

        self._flows_diag: dict[str, FlowDiagnostics] = {}
        for flow_name in self._flows:
            self._flows_diag[flow_name] = self._validate_flow(flow_name)
        for conflict in self._conflicts:
            if conflict.type == "flow" and conflict.name not in self._flows_diag:
                sources = ", ".join(str(s) for s in conflict.sources)
                self._flows_diag[conflict.name] = FlowDiagnostics(
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

    def _resolve_user_dirs(self, user_dirs: list[str | Path]) -> list[Path]:
        resolved = []
        for d in user_dirs:
            p = Path(d).expanduser().resolve()
            if not p.is_dir():
                raise FlowConfigError(f"User config directory does not exist or is not a directory: {p}")
            resolved.append(p)
        return resolved

    def _accumulate(self, kind: ResourceKind, name: str, entry: RegistryEntry[Any]) -> None:
        key = (kind, name)
        self._pending.setdefault(key, []).append(entry)

    def _resolve_pending(self) -> None:
        registry_map: dict[ResourceKind, dict[str, RegistryEntry[Any]]] = {
            "agent": self._agents,
            "phase": self._phases,
            "flow": self._flows,
            "prompt": self._prompts,
            "goal": self._goals,
            "memory_prompt": self._memories,
        }
        for (kind, name), entries in self._pending.items():
            if len(entries) > 1:
                self._conflicts.append(ConfigConflict(name=name, type=kind, sources=[e.source_file for e in entries]))
                continue
            registry_map[kind][name] = entries[0]

    def _scan_dir(self, base_dir: Path) -> None:
        for path in sorted(base_dir.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            parent_name = path.parent.name
            if parent_name == "agents":
                if suffix == ".md":
                    self._dispatch_agent_md(path)
            elif parent_name == "prompts":
                if suffix == ".md":
                    self._dispatch_prompt_md(path)
            elif suffix in {".yaml", ".yml"}:
                self._dispatch_yaml(path)

    def _dispatch_yaml(self, path: Path) -> None:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as e:
            self._record_file_error(path, str(e))
            return

        if not isinstance(raw, list):
            self._record_file_error(path, f"{path}: top-level YAML document must be a list")
            return

        for i, item in enumerate(raw):
            self._dispatch_yaml_item(path, item, i)

    def _dispatch_yaml_item(self, path: Path, item: Any, index: int) -> None:
        try:
            envelope = RESOURCE_ADAPTER.validate_python(item)
        except (ValidationError, TypeError, ValueError) as e:
            raw_name = item.get("config", {}).get("name") if isinstance(item, dict) else None
            raw_type = item.get("type") if isinstance(item, dict) else None
            if raw_name and raw_type in ("phase", "flow"):
                self._accumulate(raw_type, raw_name, BrokenEntry(source_file=path, error=str(e)))
            else:
                self._record_file_error(path, f"item {index}: {e}")
            return

        entry_ok: RegistryEntry[Any] = ValidEntry(config=envelope.config, source_file=path)
        self._accumulate(envelope.type, envelope.config.name, entry_ok)

    def _dispatch_agent_md(self, path: Path) -> None:
        stem = path.stem
        try:
            meta, body = parse_md_file(path)
        except FlowConfigError as e:
            self._accumulate("agent", stem, BrokenEntry(source_file=path, error=str(e)))
            return

        if meta.get("type") != "agent":
            self._accumulate(
                "agent",
                stem,
                BrokenEntry(source_file=path, error=f"{path}: expected type 'agent', got {meta.get('type')!r}"),
            )
            return

        fm = {k: v for k, v in meta.items() if k != "type"}
        fm["system_prompt"] = body
        try:
            config = AgentConfig.model_validate(fm)
        except ValidationError as e:
            self._accumulate("agent", stem, BrokenEntry(source_file=path, error=str(e)))
            return

        self._accumulate("agent", stem, ValidEntry(config=config, source_file=path))

    def _dispatch_prompt_md(self, path: Path) -> None:
        stem = path.stem
        try:
            meta, body = parse_md_file(path)
        except FlowConfigError as e:
            self._accumulate("prompt", stem, BrokenEntry(source_file=path, error=str(e)))
            return

        file_type = meta.get("type")
        if file_type not in PROMPT_TYPES:
            self._accumulate(
                "prompt",
                stem,
                BrokenEntry(source_file=path, error=f"{path}: expected type in {PROMPT_TYPES!r}, got {file_type!r}"),
            )
            return

        entry: RegistryEntry[str] = ValidEntry(config=body, source_file=path)
        if file_type == "prompt":
            self._accumulate("prompt", stem, entry)
        elif file_type == "goal":
            self._accumulate("goal", stem, entry)
        elif file_type == "memory_prompt":
            self._accumulate("memory_prompt", stem, entry)

    def _ok_view[C](self, registry: dict[str, RegistryEntry[C]]) -> dict[str, C]:
        return {name: e.config for name, e in registry.items() if isinstance(e, ValidEntry)}

    @cached_property
    def _ok_agents(self) -> dict[str, AgentConfig]:
        return self._ok_view(self._agents)

    @cached_property
    def _ok_prompts(self) -> dict[str, str]:
        return self._ok_view(self._prompts)

    @cached_property
    def _ok_goals(self) -> dict[str, str]:
        return self._ok_view(self._goals)

    @cached_property
    def _ok_memories(self) -> dict[str, str]:
        return self._ok_view(self._memories)

    def _validate_flow(self, flow_name: str) -> FlowDiagnostics:
        entry = self._flows[flow_name]
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

        fc: FlowConfig = entry.config

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
        """Resolve a flow's scheduled phase to its config, or the errors explaining why it can't be used."""
        phase_entry = self._phases.get(phase_name)
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
        """Explain an unresolved phase: a conflict between sources, or simply not registered."""
        conflict = next((c for c in self._conflicts if c.type == "phase" and c.name == phase_name), None)
        if conflict is not None:
            return FlowError(
                ErrorKind.PHASE,
                f"Phase {phase_name!r} referenced by flow {flow_name!r} is defined in multiple sources; "
                "resolve the conflict",
                subject=phase_name,
                phase=phase_name,
                sources=list(conflict.sources),
            )
        return FlowError(
            ErrorKind.PHASE,
            f"Phase {phase_name!r} referenced by flow {flow_name!r} is not registered",
            subject=phase_name,
            phase=phase_name,
            sources=[self._flows[flow_name].source_file],
        )

    def _validate_phase(self, pc: PhaseConfig) -> list[FlowError]:
        """Run all per-phase checks (class, agent, references)."""
        errors: list[FlowError] = []
        errors.extend(self._validate_phase_class(pc))
        errors.extend(self._validate_phase_agent(pc))
        errors.extend(self._validate_phase_refs(pc))
        return errors

    def _validate_phase_class(self, pc: PhaseConfig) -> list[FlowError]:
        phase_src = self._phases[pc.name].source_file
        if not self._phase_registry.contains(pc.class_):
            return [
                FlowError(
                    ErrorKind.PHASE,
                    f"Phase {pc.name!r} uses unknown implementation class {pc.class_!r}",
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
        agent_entry = self._agents.get(pc.agent)
        if agent_entry is None:
            return [
                FlowError(
                    ErrorKind.AGENT,
                    f"Agent {pc.agent!r} referenced by phase {pc.name!r} is not registered",
                    subject=pc.agent,
                    phase=pc.name,
                    sources=[self._phases[pc.name].source_file],
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
                errors.extend(self._check_ref(self._prompts, task.prompt_ref, ErrorKind.PROMPT, pc.name))
            if task.goal_ref is not None:
                errors.extend(self._check_ref(self._goals, task.goal_ref, ErrorKind.GOAL, pc.name))
        if pc.checkpoint is not None and pc.checkpoint.memory_prompt_ref is not None:
            errors.extend(
                self._check_ref(self._memories, pc.checkpoint.memory_prompt_ref, ErrorKind.MEMORY_PROMPT, pc.name)
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
            agents={pc.agent: self._ok_agents[pc.agent] for pc in scheduled_phases if pc.agent is not None},
            phases={pc.name: self._inline_phase(pc) for pc in scheduled_phases},
            flow=fc.flow,
            variables=resolved_variables,
        )

    def _inline_phase(self, phase: PhaseConfig) -> PhaseConfig:
        tasks = []
        for t in phase.tasks:
            upd: dict[str, Any] = {}
            if t.prompt_ref is not None:
                upd["prompt"] = self._ok_prompts[t.prompt_ref]
                upd["prompt_ref"] = None
            if t.goal_ref is not None:
                upd["goal"] = self._ok_goals[t.goal_ref]
                upd["goal_ref"] = None
            tasks.append(t.model_copy(update=upd) if upd else t)
        cp = phase.checkpoint
        if cp is not None and cp.memory_prompt_ref is not None:
            cp = cp.model_copy(
                update={"memory_prompt": self._ok_memories[cp.memory_prompt_ref], "memory_prompt_ref": None}
            )
        return phase.model_copy(update={"tasks": tasks, "checkpoint": cp})

    def _check_ref(
        self, registry: dict[str, RegistryEntry[str]], ref: str, kind: ErrorKind, phase_name: str
    ) -> list[FlowError]:
        ref_entry = registry.get(ref)
        label = kind.value.replace("_", " ").capitalize()
        if ref_entry is None:
            return [
                FlowError(
                    kind,
                    f"{label} {ref!r} referenced by phase {phase_name!r} is not registered",
                    subject=ref,
                    phase=phase_name,
                    sources=[self._phases[phase_name].source_file],
                )
            ]
        if isinstance(ref_entry, BrokenEntry):
            return [
                FlowError(
                    kind,
                    f"{label} {ref!r} referenced by phase {phase_name!r} is broken: {ref_entry.error}",
                    subject=ref,
                    phase=phase_name,
                    sources=[ref_entry.source_file],
                )
            ]
        return []

    def _validate_dependencies(self, flow_name: str, fc: FlowConfig) -> list[FlowError]:
        flow_src = self._flows[flow_name].source_file
        dependency_map: dict[str, list[str]] = {fe.phase: fe.dependencies for fe in fc.flow}
        errors: list[FlowError] = []
        errors.extend(self._check_duplicate_schedule(fc, flow_name, flow_src))
        errors.extend(self._check_unscheduled_dependencies(fc, dependency_map, flow_name, flow_src))
        errors.extend(self._check_dependency_cycles(dependency_map, flow_name, flow_src))
        return errors

    def _check_duplicate_schedule(self, fc: FlowConfig, flow_name: str, flow_src: Path) -> list[FlowError]:
        errors: list[FlowError] = []
        seen: set[str] = set()
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
        self, fc: FlowConfig, dependency_map: dict[str, list[str]], flow_name: str, flow_src: Path
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
        self, dependency_map: dict[str, list[str]], flow_name: str, flow_src: Path
    ) -> list[FlowError]:
        errors: list[FlowError] = []
        cycles, truncated = detect_cycles(dependency_map)
        for cycle in cycles:
            path = " -> ".join(cycle)
            errors.append(
                FlowError(
                    ErrorKind.DEPENDENCY, f"Dependency cycle detected in flow {flow_name!r}: {path}", sources=[flow_src]
                )
            )
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
            phase_src = self._phases[pc.name].source_file
            if pc.agent is not None and pc.agent in self._ok_agents:
                agent_src = self._agents[pc.agent].source_file
                for v in self._ok_agents[pc.agent].variables:
                    declared.append(_DeclaredVar(v.name, v.default, f"agent {pc.agent!r}", agent_src))
            for v in pc.variables:
                declared.append(_DeclaredVar(v.name, v.default, f"phase {pc.name!r}", phase_src))
        return declared

    def _collect_default_values(self, declared: list[_DeclaredVar]) -> tuple[dict[str, str], list[FlowError]]:
        by_name: dict[str, dict[str, list[str]]] = {}
        sources_by_name: dict[str, list[Path]] = {}
        for d in declared:
            if d.default is None:
                continue
            by_name.setdefault(d.name, {}).setdefault(d.default, []).append(d.origin)
            srcs = sources_by_name.setdefault(d.name, [])
            if d.source not in srcs:
                srcs.append(d.source)
        defaults: dict[str, str] = {}
        errors: list[FlowError] = []
        for name, value_origins in by_name.items():
            if len(value_origins) > 1:
                detail = "; ".join(f"{value!r} from {', '.join(origins)}" for value, origins in value_origins.items())
                errors.append(
                    FlowError(
                        ErrorKind.VARIABLE,
                        f"Variable {name!r} has conflicting defaults: {detail}",
                        subject=name,
                        sources=sources_by_name[name],
                    )
                )
            else:
                defaults[name] = next(iter(value_origins))
        return defaults, errors

    def _find_missing_variables(self, declared: list[_DeclaredVar], fc: FlowConfig) -> list[FlowError]:
        has_default = {d.name for d in declared if d.default is not None}
        origins_by_name: dict[str, list[str]] = {}
        sources_by_name: dict[str, list[Path]] = {}
        for d in declared:
            origins = origins_by_name.setdefault(d.name, [])
            if d.origin not in origins:
                origins.append(d.origin)
            srcs = sources_by_name.setdefault(d.name, [])
            if d.source not in srcs:
                srcs.append(d.source)
        errors: list[FlowError] = []
        for name, origins in origins_by_name.items():
            if name not in has_default and name not in fc.variables:
                errors.append(
                    FlowError(
                        ErrorKind.VARIABLE,
                        f"Required variable {name!r} has no default and is not supplied by the flow "
                        f"(declared in {', '.join(origins)})",
                        subject=name,
                        sources=sources_by_name[name],
                    )
                )
        return errors

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
        diag = self._flows_diag.get(name)
        if diag is None:
            raise FlowConfigError(f"Flow {name!r} not found{self._file_errors_note()}")
        if diag.status is ConfigStatus.BROKEN:
            raise FlowConfigError(f"Flow {name!r} is invalid:\n" + "\n".join(f"  {e.message}" for e in diag.errors))
        if diag.resolved is None:
            raise FlowConfigError(f"Flow {name!r} passed validation but produced no resolved flow (engine bug)")
        return diag.resolved

    @property
    def flows(self) -> dict[str, FlowDiagnostics]:
        return self._flows_diag

    @property
    def file_errors(self) -> dict[Path, str]:
        return dict(self._file_errors)

    @property
    def has_conflicts(self) -> bool:
        return bool(self._conflicts)

    @property
    def conflicts(self) -> list[ConfigConflict]:
        return self._conflicts
