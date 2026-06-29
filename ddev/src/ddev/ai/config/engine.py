# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

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
    VariableDeclaration,
)

if TYPE_CHECKING:
    from ddev.ai.phases.base import Phase

ResourceKind = Literal["agent", "phase", "flow", "prompt", "goal", "memory"]


class ConfigStatus(StrEnum):
    OK = "ok"
    BROKEN = "broken"


@dataclass
class ValidEntry[C]:
    config: C
    source_file: Path
    overridden: list[Path] = field(default_factory=list)


@dataclass
class BrokenEntry:
    source_file: Path
    error: str
    overridden: list[Path] = field(default_factory=list)


type RegistryEntry[C] = ValidEntry[C] | BrokenEntry


@dataclass
class ConfigConflict:
    name: str
    type: ResourceKind
    sources: list[Path]


@dataclass
class FlowDiagnostics:
    name: str
    status: ConfigStatus
    errors: list[str]
    resolved: ResolvedFlow | None = None


class PhaseRegistry(Protocol):
    def contains(self, name: str) -> bool: ...
    def get(self, name: str) -> type[Phase]: ...


RESOURCE_ADAPTER: TypeAdapter[PhaseEnvelope | FlowEnvelope] = TypeAdapter(ResourceEnvelope)

PROMPT_TYPES = {"prompt", "goal", "memory"}


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
        self._core_dir = core_dir

        resolved_user_dirs = self._resolve_user_dirs(user_dirs)

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
                    [f"Flow {conflict.name!r} has conflicting definitions: {sources}"],
                )

    def _resolve_user_dirs(self, user_dirs: list[str | Path]) -> list[Path]:
        resolved = []
        for d in user_dirs:
            p = Path(d).expanduser().resolve()
            if not p.is_dir():
                raise FlowConfigError(f"User config directory does not exist or is not a directory: {p}")
            resolved.append(p)
        return resolved

    def _is_core(self, path: Path) -> bool:
        return path.resolve().is_relative_to(self._core_dir.resolve())

    def _accumulate(self, kind: ResourceKind, name: str, entry: RegistryEntry[Any]) -> None:
        key = (kind, name)
        self._pending.setdefault(key, []).append(entry)

    def _resolve_bucket(
        self, kind: ResourceKind, name: str, entries: list[RegistryEntry[Any]]
    ) -> RegistryEntry[Any] | None:
        core = [e for e in entries if self._is_core(e.source_file)]
        user = [e for e in entries if not self._is_core(e.source_file)]
        if len(core) > 1 or len(user) > 1:
            self._conflicts.append(ConfigConflict(name=name, type=kind, sources=[e.source_file for e in entries]))
            return None
        winner = user[0] if user else core[0]
        if user and core:
            winner.overridden = [core[0].source_file]
        return winner

    def _resolve_pending(self) -> None:
        registry_map: dict[ResourceKind, dict[str, RegistryEntry[Any]]] = {
            "agent": self._agents,
            "phase": self._phases,
            "flow": self._flows,
            "prompt": self._prompts,
            "goal": self._goals,
            "memory": self._memories,
        }
        for (kind, name), entries in self._pending.items():
            winner = self._resolve_bucket(kind, name, entries)
            if winner is not None:
                registry_map[kind][name] = winner

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
        elif file_type == "memory":
            self._accumulate("memory", stem, entry)

    def _validate_flow(self, flow_name: str) -> FlowDiagnostics:
        entry = self._flows[flow_name]
        if isinstance(entry, BrokenEntry):
            return FlowDiagnostics(flow_name, ConfigStatus.BROKEN, [entry.error or "broken flow"])

        fc: FlowConfig = entry.config
        errors: list[str] = []

        ok_agents = {name: e.config for name, e in self._agents.items() if isinstance(e, ValidEntry)}

        scheduled_phases: list[PhaseConfig] = []
        for fe in fc.flow:
            phase_entry = self._phases.get(fe.phase)
            if phase_entry is None:
                errors.append(
                    f"Phase {fe.phase!r} referenced by flow {flow_name!r} is not registered{self._file_errors_note()}"
                )
                continue
            if isinstance(phase_entry, BrokenEntry):
                errors.append(f"Phase {fe.phase!r} referenced by flow {flow_name!r} is broken")
                continue
            pc: PhaseConfig = phase_entry.config
            scheduled_phases.append(pc)

            if self._phase_registry.contains(pc.class_):
                try:
                    self._phase_registry.get(pc.class_).validate_config(pc.name, pc, ok_agents)
                except FlowConfigError as e:
                    errors.append(str(e))
            else:
                errors.append(f"Phase {pc.name!r} uses unknown implementation class {pc.class_!r}")

            if pc.agent is not None:
                agent_entry = self._agents.get(pc.agent)
                if agent_entry is None:
                    errors.append(
                        f"Agent {pc.agent!r} referenced by phase {pc.name!r} is not registered"
                        f"{self._file_errors_note()}"
                    )
                elif isinstance(agent_entry, BrokenEntry):
                    errors.append(f"Agent {pc.agent!r} referenced by phase {pc.name!r} is broken")

            for task in pc.tasks:
                if task.prompt_ref is not None:
                    errors.extend(self._check_ref(self._prompts, task.prompt_ref, "prompt", pc.name))
                if task.goal_ref is not None:
                    errors.extend(self._check_ref(self._goals, task.goal_ref, "goal", pc.name))
            if pc.checkpoint is not None and pc.checkpoint.memory_prompt_ref is not None:
                errors.extend(self._check_ref(self._memories, pc.checkpoint.memory_prompt_ref, "memory", pc.name))

        errors.extend(self._validate_dependencies(flow_name, fc))
        resolved_variables, var_errors = self._resolve_variables(scheduled_phases, fc, ok_agents)
        errors.extend(var_errors)

        if errors:
            return FlowDiagnostics(flow_name, ConfigStatus.BROKEN, errors)

        ok_prompts = {n: e.config for n, e in self._prompts.items() if isinstance(e, ValidEntry)}
        ok_goals = {n: e.config for n, e in self._goals.items() if isinstance(e, ValidEntry)}
        ok_memories = {n: e.config for n, e in self._memories.items() if isinstance(e, ValidEntry)}

        resolved = ResolvedFlow(
            name=flow_name,
            agents={pc.agent: ok_agents[pc.agent] for pc in scheduled_phases if pc.agent is not None},
            phases={pc.name: self._inline(pc, ok_prompts, ok_goals, ok_memories) for pc in scheduled_phases},
            flow=fc.flow,
            variables=resolved_variables,
        )
        return FlowDiagnostics(flow_name, ConfigStatus.OK, [], resolved=resolved)

    def _check_ref(self, registry: dict[str, RegistryEntry[str]], ref: str, kind: str, phase_name: str) -> list[str]:
        ref_entry = registry.get(ref)
        if ref_entry is None:
            return [
                f"{kind.capitalize()} {ref!r} referenced by phase {phase_name!r} is not registered"
                f"{self._file_errors_note()}"
            ]
        if isinstance(ref_entry, BrokenEntry):
            return [f"{kind.capitalize()} {ref!r} referenced by phase {phase_name!r} is broken"]
        return []

    def _validate_dependencies(self, flow_name: str, fc: FlowConfig) -> list[str]:
        errors: list[str] = []
        dependency_map: dict[str, list[str]] = {}
        for fe in fc.flow:
            if fe.phase in dependency_map:
                errors.append(f"Phase {fe.phase!r} is scheduled more than once in flow {flow_name!r}")
            dependency_map[fe.phase] = fe.dependencies

        for fe in fc.flow:
            for dep in fe.dependencies:
                if dep not in dependency_map:
                    errors.append(
                        f"Phase {fe.phase!r} depends on {dep!r}, which is not scheduled in flow {flow_name!r}"
                    )

        cycles, truncated = detect_cycles(dependency_map)
        for cycle in cycles:
            path = " -> ".join(cycle)
            errors.append(f"Dependency cycle detected in flow {flow_name!r}: {path}")
        if truncated:
            errors.append(f"Cycle detection truncated in flow {flow_name!r} (too many cycles)")
        return errors

    def _resolve_variables(
        self, scheduled_phases: list[PhaseConfig], fc: FlowConfig, ok_agents: dict[str, AgentConfig]
    ) -> tuple[dict[str, str], list[str]]:
        declarations: list[VariableDeclaration] = []
        for pc in scheduled_phases:
            if pc.agent is not None and pc.agent in ok_agents:
                declarations.extend(ok_agents[pc.agent].variables)
            declarations.extend(pc.variables)

        errors: list[str] = []
        defaults: dict[str, str] = {}
        seen_defaults: dict[str, str] = {}
        declared_names: set[str] = set()
        for decl in declarations:
            declared_names.add(decl.name)
            if decl.default is None:
                continue
            if decl.name in seen_defaults and seen_defaults[decl.name] != decl.default:
                errors.append(
                    f"Variable {decl.name!r} has conflicting defaults: {seen_defaults[decl.name]!r} vs {decl.default!r}"
                )
            else:
                seen_defaults[decl.name] = decl.default
                defaults[decl.name] = decl.default

        for name in declared_names:
            if name not in defaults and name not in fc.variables:
                errors.append(f"Required variable {name!r} has no default and is not supplied by the flow")

        resolved = {**defaults, **fc.variables}
        return resolved, errors

    def _inline(
        self, phase: PhaseConfig, prompts: dict[str, str], goals: dict[str, str], memories: dict[str, str]
    ) -> PhaseConfig:
        tasks = []
        for t in phase.tasks:
            upd: dict[str, Any] = {}
            if t.prompt_ref is not None:
                upd["prompt"] = prompts[t.prompt_ref]
                upd["prompt_ref"] = None
            if t.goal_ref is not None:
                upd["goal"] = goals[t.goal_ref]
                upd["goal_ref"] = None
            tasks.append(t.model_copy(update=upd) if upd else t)
        cp = phase.checkpoint
        if cp is not None and cp.memory_prompt_ref is not None:
            cp = cp.model_copy(update={"memory_prompt": memories[cp.memory_prompt_ref], "memory_prompt_ref": None})
        return phase.model_copy(update={"tasks": tasks, "checkpoint": cp})

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
            raise FlowConfigError(f"Flow {name!r} is invalid:\n" + "\n".join(f"  {e}" for e in diag.errors))
        assert diag.resolved is not None
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
