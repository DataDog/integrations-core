# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import TypeAdapter, ValidationError

from ddev.ai.config.errors import FlowConfigError, detect_cycles
from ddev.ai.config.models import (
    AgentConfig,
    FlowConfig,
    PhaseConfig,
    ResolvedFlow,
    ResourceEnvelope,
    VariableDeclaration,
)
ResourceKind = Literal["agent", "phase", "flow"]

_log = logging.getLogger(__name__)



@dataclass
class ConfigConflict:
    name: str
    type: ResourceKind
    sources: list[Path]


@dataclass
class _RegistryEntry[C]:
    config: C
    source_file: Path


@dataclass
class _VarState:
    default: str | None
    sources: list[str] = field(default_factory=list)

    @property
    def has_default(self) -> bool:
        return self.default is not None


_ENVELOPE_ADAPTER: TypeAdapter[ResourceEnvelope] = TypeAdapter(ResourceEnvelope)

# Absolute paths to the ddev-shipped flows and phases directories.
CORE_FLOWS_DIR: Path = Path(__file__).parent.parent / "flows"


class ConfigurationEngine:
    """Parses typed resource objects from YAML files for a specific named flow."""

    def __init__(
        self,
        flow_name: str,
        user_dirs: list[str] | None = None,
        *,
        core_dir: Path = CORE_FLOWS_DIR,
    ) -> None:
        self._flow_name = flow_name
        self._core_dir = core_dir
        all_base_dirs = [core_dir] + self._resolve_user_dirs(user_dirs or [])
        self._scan_dirs: list[Path] = self._deduplicate(self._expand_flow_dirs(all_base_dirs, flow_name))
        self._agents: dict[str, _RegistryEntry[AgentConfig]] = {}
        self._phases: dict[str, _RegistryEntry[PhaseConfig]] = {}
        self._flows: dict[str, _RegistryEntry[FlowConfig]] = {}
        self._conflicts: list[ConfigConflict] = []
        self._file_errors: dict[Path, str] = {}
        self._build_registries()

    def _expand_flow_dirs(self, base_dirs: list[Path], flow_name: str) -> list[Path]:
        """For each base dir, include <base>/<flow_name>/ and <base>/shared/ if they exist."""
        result = []
        for base in base_dirs:
            flow_sub = base / flow_name
            if flow_sub.is_dir():
                result.append(flow_sub)
            shared_sub = base / "shared"
            if shared_sub.is_dir():
                result.append(shared_sub)
        return result

    def _deduplicate(self, dirs: list[Path]) -> list[Path]:
        seen: set[Path] = set()
        result: list[Path] = []
        for d in dirs:
            resolved = d.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(d)
        return result

    def _resolve_user_dirs(self, raw_dirs: list[str]) -> list[Path]:
        resolved = []
        for raw in raw_dirs:
            path = Path(raw).expanduser().resolve()
            if not path.is_dir():
                raise FlowConfigError(f"User flow directory does not exist: {path}")
            resolved.append(path)
        return resolved

    def _build_registries(self) -> None:
        pending: dict[tuple[ResourceKind, str], list[_RegistryEntry[Any]]] = {}
        seen_files: set[Path] = set()

        for scan_dir in self._scan_dirs:
            for yaml_file in sorted(scan_dir.rglob("*.yaml")) + sorted(scan_dir.rglob("*.yml")):
                resolved = yaml_file.resolve()
                if resolved in seen_files:
                    continue
                seen_files.add(resolved)
                try:
                    self._parse_file(yaml_file, pending)
                except FlowConfigError as e:
                    self._file_errors[yaml_file] = str(e)

        for (obj_type, name), entries in pending.items():
            if len(entries) > 1:
                self._conflicts.append(
                    ConfigConflict(
                        name=name,
                        type=obj_type,
                        sources=[e.source_file for e in entries],
                    )
                )
            else:
                registry = self._registry_for(obj_type)
                registry[name] = entries[0]

    def _parse_file(
        self,
        path: Path,
        pending: dict[tuple[ResourceKind, str], list[_RegistryEntry[Any]]],
    ) -> None:
        try:
            text = path.read_text()
        except OSError as e:
            raise FlowConfigError(f"Could not read {path}: {e}") from e

        try:
            raw_list = yaml.safe_load(text)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            location = f" at line {mark.line + 1}" if mark else ""
            raise FlowConfigError(f"Malformed YAML in {path}{location}: {e}") from e

        if not isinstance(raw_list, list):
            raise FlowConfigError(f"{path}: expected a YAML list of resource objects, got {type(raw_list).__name__}")

        for i, raw in enumerate(raw_list):
            try:
                envelope = _ENVELOPE_ADAPTER.validate_python(raw)
            except ValidationError as e:
                raise FlowConfigError(f"{path} item {i}: {e}") from e

            entry = _RegistryEntry(config=envelope.config, source_file=path)
            key = (envelope.type, envelope.config.name)
            pending.setdefault(key, []).append(entry)

    def _registry_for(self, obj_type: ResourceKind) -> dict[str, _RegistryEntry[Any]]:
        match obj_type:
            case "agent":
                return self._agents
            case "phase":
                return self._phases
            case "flow":
                return self._flows
            case _:
                raise AssertionError(f"Unknown resource type: {obj_type!r}")

    @property
    def has_conflicts(self) -> bool:
        return bool(self._conflicts)

    @property
    def conflicts(self) -> list[ConfigConflict]:
        return list(self._conflicts)

    @staticmethod
    def get_agent_prompt(agent_name: str, flow_dir: Path) -> Path:
        """Return the conventional system prompt path for an agent."""
        return flow_dir / "prompts" / f"{agent_name}.md"

    def build_flow(self) -> ResolvedFlow:
        """Validate and return a fully resolved flow. Raises FlowConfigError on any problem."""
        name = self._flow_name
        self._check_no_conflicts()
        flow_config = self._get_flow_config(name)
        phases = self._collect_phases(flow_config, name)
        agents = self._collect_agents(phases)
        self._validate_dependency_graph(flow_config, name)
        variables = self._resolve_variables(name, flow_config, phases, agents)
        return ResolvedFlow(
            name=name,
            agents={n: self._resolve_agent_paths(c, self._agents[n].source_file) for n, c in agents.items()},
            phases={n: self._resolve_phase_paths(c, self._phases[n].source_file) for n, c in phases.items()},
            flow=flow_config.flow,
            variables=variables,
        )

    def _check_no_conflicts(self) -> None:
        if not self.has_conflicts:
            return
        lines = "\n".join(
            f"  {c.type} {c.name!r}: defined in {', '.join(str(s) for s in c.sources)}" for c in self._conflicts
        )
        raise FlowConfigError(f"Configuration conflicts must be resolved before building a flow:\n{lines}")

    def _format_file_errors(self) -> str:
        if not self._file_errors:
            return ""
        lines = "\n".join(f"  {p}: {e}" for p, e in self._file_errors.items())
        return f"\nNote: these files failed to parse and may contain the missing resource:\n{lines}"

    def _get_flow_config(self, name: str) -> FlowConfig:
        if name not in self._flows:
            raise FlowConfigError(
                f"Flow {name!r} not found. Available flows: {sorted(self._flows)}"
                + self._format_file_errors()
            )
        return self._flows[name].config

    def _collect_phases(self, flow_config: FlowConfig, flow_name: str) -> dict[str, PhaseConfig]:
        phases = {}
        seen: set[str] = set()
        for entry in flow_config.flow:
            if entry.phase in seen:
                raise FlowConfigError(f"Duplicate phase in flow {flow_name!r}: {entry.phase!r}")
            seen.add(entry.phase)
            if entry.phase not in self._phases:
                raise FlowConfigError(
                    f"Flow {flow_name!r} references unknown phase: {entry.phase!r}"
                    + self._format_file_errors()
                )
            phases[entry.phase] = self._phases[entry.phase].config
        return phases

    def _collect_agents(self, phases: dict[str, PhaseConfig]) -> dict[str, AgentConfig]:
        agents = {}
        for phase_name, phase_config in phases.items():
            if phase_config.agent is None:
                continue
            if phase_config.agent not in self._agents:
                raise FlowConfigError(
                    f"Phase {phase_name!r} references unknown agent: {phase_config.agent!r}"
                    + self._format_file_errors()
                )
            agents[phase_config.agent] = self._agents[phase_config.agent].config
        return agents

    def _validate_dependency_graph(self, flow_config: FlowConfig, flow_name: str) -> None:
        scheduled = {entry.phase for entry in flow_config.flow}
        dependency_map = {}
        for entry in flow_config.flow:
            for dep in entry.dependencies:
                if dep not in scheduled:
                    raise FlowConfigError(
                        f"Phase {entry.phase!r} depends on {dep!r} which is not in flow {flow_name!r}"
                    )
            dependency_map[entry.phase] = entry.dependencies
        cycles, truncated = detect_cycles(dependency_map)
        if cycles:
            formatted = "\n  ".join(" → ".join(c) for c in cycles)
            suffix = f"\n  (showing first {len(cycles)}; more cycles exist)" if truncated else ""
            raise FlowConfigError(f"Cycle(s) detected in flow {flow_name!r}:\n  {formatted}{suffix}")

    def _resolve_variables(
        self,
        flow_name: str,
        flow_config: FlowConfig,
        phases: dict[str, PhaseConfig],
        agents: dict[str, AgentConfig],
    ) -> dict[str, str]:
        declarations = self._gather_variable_declarations(phases, agents, flow_name)
        return self._apply_variable_values(declarations, flow_config, flow_name)

    def _gather_variable_declarations(
        self,
        phases: dict[str, PhaseConfig],
        agents: dict[str, AgentConfig],
        flow_name: str,
    ) -> dict[str, _VarState]:
        """Collect variable declarations from all agents and phases; raise on conflicting defaults."""
        declarations: dict[str, _VarState] = {}
        all_objects: list[tuple[str, AgentConfig | PhaseConfig]] = [(f"agent:{n}", c) for n, c in agents.items()] + [
            (f"phase:{n}", c) for n, c in phases.items()
        ]
        for source_label, obj in all_objects:
            for var_decl in obj.variables:
                self._register_declaration(declarations, var_decl, source_label, flow_name)
        return declarations

    def _register_declaration(
        self,
        declarations: dict[str, _VarState],
        var_decl: VariableDeclaration,
        source_label: str,
        flow_name: str,
    ) -> None:
        """Add one variable declaration, raising if its default conflicts with an existing one."""
        if var_decl.name not in declarations:
            declarations[var_decl.name] = _VarState(default=var_decl.default, sources=[source_label])
            return
        existing = declarations[var_decl.name]
        if existing.has_default and var_decl.default is not None and existing.default != var_decl.default:
            existing.sources.append(source_label)
            all_sources = ", ".join(existing.sources)
            raise FlowConfigError(
                f"Variable {var_decl.name!r} has conflicting default values across {all_sources} in flow {flow_name!r}"
            )
        existing.sources.append(source_label)
        if not existing.has_default and var_decl.default is not None:
            existing.default = var_decl.default

    def _apply_variable_values(
        self,
        declarations: dict[str, _VarState],
        flow_config: FlowConfig,
        flow_name: str,
    ) -> dict[str, str]:
        """Resolve each declaration to a value; raise listing any variables with no value or default."""
        resolved: dict[str, str] = {}
        missing: list[str] = []
        for var_name, state in declarations.items():
            if var_name in flow_config.variables:
                resolved[var_name] = flow_config.variables[var_name]
            elif state.default is not None:
                resolved[var_name] = state.default
            else:
                missing.append(f"  {var_name!r} (declared in {', '.join(state.sources)})")
        if missing:
            raise FlowConfigError(f"Flow {flow_name!r} is missing required variable values:\n" + "\n".join(missing))
        return resolved

    @staticmethod
    def _resolve_relative(base: Path, p: Path | None) -> Path | None:
        """Resolve p relative to base if it is not already absolute."""
        if p is not None and not p.is_absolute():
            return base / p
        return p

    def _resolve_agent_paths(self, config: AgentConfig, source_file: Path) -> AgentConfig:
        source_dir = source_file.parent
        if config.system_prompt_path is None:
            system_prompt = self.get_agent_prompt(config.name, source_dir)
        elif not config.system_prompt_path.is_absolute():
            system_prompt = source_dir / config.system_prompt_path
        else:
            system_prompt = config.system_prompt_path
        if not system_prompt.exists():
            raise FlowConfigError(f"System prompt not found for agent {config.name!r}: {system_prompt}")
        if system_prompt == config.system_prompt_path:
            return config
        return config.model_copy(update={"system_prompt_path": system_prompt})

    def _resolve_phase_paths(self, config: PhaseConfig, source_file: Path) -> PhaseConfig:
        source_dir = source_file.parent
        resolved_tasks = []
        for task in config.tasks:
            updates: dict[str, Any] = {}
            new_prompt = self._resolve_relative(source_dir, task.prompt_path)
            if new_prompt is not task.prompt_path:
                updates["prompt_path"] = new_prompt
            if new_prompt is not None and not new_prompt.exists():
                raise FlowConfigError(f"Prompt not found for task {task.name!r} in phase {config.name!r}: {new_prompt}")
            new_goal = self._resolve_relative(source_dir, task.goal_path)
            if new_goal is not task.goal_path:
                updates["goal_path"] = new_goal
            if new_goal is not None and not new_goal.exists():
                raise FlowConfigError(f"Goal not found for task {task.name!r} in phase {config.name!r}: {new_goal}")
            resolved_tasks.append(task.model_copy(update=updates) if updates else task)

        checkpoint = config.checkpoint
        if checkpoint is not None:
            new_memory = self._resolve_relative(source_dir, checkpoint.memory_prompt_path)
            if new_memory is not checkpoint.memory_prompt_path:
                checkpoint = checkpoint.model_copy(update={"memory_prompt_path": new_memory})
            if new_memory is not None and not new_memory.exists():
                raise FlowConfigError(f"Memory prompt not found for phase {config.name!r}: {new_memory}")

        return config.model_copy(update={"tasks": resolved_tasks, "checkpoint": checkpoint})
