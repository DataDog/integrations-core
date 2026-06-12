# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from ddev.ai.config.models import (
    AgentConfig,
    FlowConfig,
    PhaseConfig,
    ResolvedFlow,
    ResourceEnvelope,
    VariableDeclaration,
)
from ddev.ai.phases.config import FlowConfigError, detect_cycles


@dataclass
class ConfigConflict:
    name: str
    type: str  # "agent", "phase", or "flow"
    sources: list[Path]


@dataclass
class _RegistryEntry:
    config: AgentConfig | PhaseConfig | FlowConfig
    source_file: Path


_ENVELOPE_ADAPTER: TypeAdapter[ResourceEnvelope] = TypeAdapter(ResourceEnvelope)

# Absolute path to the ddev-shipped flow configs directory.
CORE_FLOWS_DIR: Path = Path(__file__).parent.parent / "flows"


class ConfigurationEngine:
    """Parses typed resource objects from YAML files in one or more directories."""

    def __init__(
        self,
        core_dir: Path,
        user_dirs: list[str] | None = None,
    ) -> None:
        self._core_dir = core_dir
        self._scan_dirs: list[Path] = [core_dir] + self._resolve_user_dirs(user_dirs or [])
        self._agents: dict[str, _RegistryEntry] = {}
        self._phases: dict[str, _RegistryEntry] = {}
        self._flows: dict[str, _RegistryEntry] = {}
        self._conflicts: list[ConfigConflict] = []
        self._build_registries()

    @classmethod
    def from_user_dirs(cls, user_dirs: list[str] | None = None) -> ConfigurationEngine:
        """Create an engine scanning the core flows dir plus any user-provided dirs."""
        return cls(core_dir=CORE_FLOWS_DIR, user_dirs=user_dirs or [])

    def _resolve_user_dirs(self, raw_dirs: list[str]) -> list[Path]:
        resolved = []
        for raw in raw_dirs:
            path = Path(raw).expanduser().resolve()
            if not path.is_dir():
                raise FlowConfigError(f"User flow directory does not exist: {path}")
            resolved.append(path)
        return resolved

    def _build_registries(self) -> None:
        pending: dict[tuple[str, str], list[_RegistryEntry]] = {}

        for scan_dir in self._scan_dirs:
            for yaml_file in sorted(scan_dir.rglob("*.yaml")) + sorted(scan_dir.rglob("*.yml")):
                self._parse_file(yaml_file, pending)

        for (obj_type, name), entries in pending.items():
            if len(entries) > 1:
                self._conflicts.append(
                    ConfigConflict(
                        name=name,
                        type=obj_type,
                        sources=[e.source_file for e in entries],
                    )
                )
            registry = self._registry_for(obj_type)
            registry[name] = entries[-1]

    def _parse_file(
        self,
        path: Path,
        pending: dict[tuple[str, str], list[_RegistryEntry]],
    ) -> None:
        try:
            raw_list = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError) as e:
            raise FlowConfigError(f"Failed to load {path}: {e}") from e

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

    def _registry_for(self, obj_type: str) -> dict[str, _RegistryEntry]:
        if obj_type == "agent":
            return self._agents
        if obj_type == "phase":
            return self._phases
        if obj_type == "flow":
            return self._flows
        raise AssertionError(f"Unknown resource type: {obj_type!r}")

    @property
    def has_conflicts(self) -> bool:
        return bool(self._conflicts)

    @property
    def conflicts(self) -> list[ConfigConflict]:
        return list(self._conflicts)

    def build_flow(self, name: str) -> ResolvedFlow:
        """Validate and return a fully resolved flow. Raises FlowConfigError on any problem."""
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

    def _get_flow_config(self, name: str) -> FlowConfig:
        if name not in self._flows:
            raise FlowConfigError(f"Flow {name!r} not found. Available flows: {sorted(self._flows)}")
        return self._flows[name].config  # type: ignore[return-value]

    def _collect_phases(self, flow_config: FlowConfig, flow_name: str) -> dict[str, PhaseConfig]:
        phases = {}
        seen: set[str] = set()
        for entry in flow_config.flow:
            if entry.phase in seen:
                raise FlowConfigError(f"Duplicate phase in flow {flow_name!r}: {entry.phase!r}")
            seen.add(entry.phase)
            if entry.phase not in self._phases:
                raise FlowConfigError(f"Flow {flow_name!r} references unknown phase: {entry.phase!r}")
            phases[entry.phase] = self._phases[entry.phase].config  # type: ignore[assignment]
        return phases

    def _collect_agents(self, phases: dict[str, PhaseConfig]) -> dict[str, AgentConfig]:
        agents = {}
        for phase_name, phase_config in phases.items():
            if phase_config.agent is None:
                continue
            if phase_config.agent not in self._agents:
                raise FlowConfigError(f"Phase {phase_name!r} references unknown agent: {phase_config.agent!r}")
            agents[phase_config.agent] = self._agents[phase_config.agent].config  # type: ignore[assignment]
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
    ) -> dict[str, dict]:
        """Collect variable declarations from all agents and phases; raise on conflicting defaults."""
        declarations: dict[str, dict] = {}
        all_objects: list[tuple[str, AgentConfig | PhaseConfig]] = [(f"agent:{n}", c) for n, c in agents.items()] + [
            (f"phase:{n}", c) for n, c in phases.items()
        ]
        for source_label, obj in all_objects:
            for var_decl in obj.variables:
                self._register_declaration(declarations, var_decl, source_label, flow_name)
        return declarations

    def _register_declaration(
        self,
        declarations: dict[str, dict],
        var_decl: VariableDeclaration,
        source_label: str,
        flow_name: str,
    ) -> None:
        """Add one variable declaration, raising if its default conflicts with an existing one."""
        if var_decl.name not in declarations:
            declarations[var_decl.name] = {
                "default": var_decl.default,
                "has_default": var_decl.default is not None,
                "sources": [source_label],
            }
            return
        existing = declarations[var_decl.name]
        existing["sources"].append(source_label)
        if existing["has_default"] and var_decl.default is not None and existing["default"] != var_decl.default:
            all_sources = ", ".join(existing["sources"])
            raise FlowConfigError(
                f"Variable {var_decl.name!r} has conflicting default values across {all_sources} in flow {flow_name!r}"
            )
        if not existing["has_default"] and var_decl.default is not None:
            existing["default"] = var_decl.default
            existing["has_default"] = True

    def _apply_variable_values(
        self,
        declarations: dict[str, dict],
        flow_config: FlowConfig,
        flow_name: str,
    ) -> dict[str, str]:
        """Resolve each declaration to a value; raise listing any variables with no value or default."""
        resolved: dict[str, str] = {}
        missing: list[str] = []
        for var_name, info in declarations.items():
            if var_name in flow_config.variables:
                resolved[var_name] = flow_config.variables[var_name]
            elif info["has_default"]:
                resolved[var_name] = info["default"]  # type: ignore[assignment]
            else:
                missing.append(f"  {var_name!r} (declared in {', '.join(info['sources'])})")
        if missing:
            raise FlowConfigError(f"Flow {flow_name!r} is missing required variable values:\n" + "\n".join(missing))
        return resolved

    def _resolve_agent_paths(self, config: AgentConfig, source_file: Path) -> AgentConfig:
        source_dir = source_file.parent
        system_prompt = source_dir / "prompts" / f"{config.name}.md"
        return config.model_copy(update={"system_prompt_path": system_prompt})

    def _resolve_phase_paths(self, config: PhaseConfig, source_file: Path) -> PhaseConfig:
        source_dir = source_file.parent
        resolved_tasks = []
        for task in config.tasks:
            updates: dict = {}
            if task.prompt_path is not None and not task.prompt_path.is_absolute():
                updates["prompt_path"] = source_dir / task.prompt_path
            if task.goal_path is not None and not task.goal_path.is_absolute():
                updates["goal_path"] = source_dir / task.goal_path
            resolved_tasks.append(task.model_copy(update=updates) if updates else task)

        checkpoint = config.checkpoint
        if checkpoint is not None and checkpoint.memory_prompt_path is not None:
            if not checkpoint.memory_prompt_path.is_absolute():
                checkpoint = checkpoint.model_copy(
                    update={"memory_prompt_path": source_dir / checkpoint.memory_prompt_path}
                )

        return config.model_copy(update={"tasks": resolved_tasks, "checkpoint": checkpoint})
