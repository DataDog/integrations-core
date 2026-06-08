# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.base import FlowContext, Phase
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, FlowConfig, FlowConfigError
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator


class PhaseRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, type[Phase]] = {}

    def register(self, name: str, phase_cls: type[Phase]) -> None:
        self._registry[name] = phase_cls

    def known_names(self) -> list[str]:
        return sorted(self._registry)

    def get(self, name: str) -> type[Phase]:
        if name not in self._registry:
            raise ValueError(f"Unknown phase type: {name!r}. Known: {self.known_names()}")
        return self._registry[name]


class ResourceUnavailableError(Exception):
    """Raised when a phase requests a resource the provider cannot supply."""


class ResourceProvider:
    """Supplies the raw resources phases combine to build their agents/tools.

    Holds raw infrastructure (agent clients, file access policy) and the flow's agent
    definitions. Assembled objects (agent/subagent builders) are NOT stored here — phases
    construct those inside build(). One instance is shared by every phase in a run, so
    file_registry() is a lazily-constructed singleton (global read-before-write consistency).
    """

    def __init__(
        self,
        agent_clients: dict[str, Any],
        file_access_policy: FileAccessPolicy,
        agents: dict[str, AgentConfig],
    ) -> None:
        self._agent_clients = agent_clients
        self._file_access_policy = file_access_policy
        self._agents = agents
        self._file_registry: FileRegistry | None = None

    def agent_clients(self) -> dict[str, Any]:
        """Raw provider-name -> SDK client map."""
        return dict(self._agent_clients)

    def file_registry(self) -> FileRegistry:
        """Lazily-built, run-wide singleton FileRegistry."""
        if self._file_registry is None:
            self._file_registry = FileRegistry(policy=self._file_access_policy)
        return self._file_registry

    def agent_config(self, name: str) -> AgentConfig:
        """Resolve a flow agent definition by name; typed error if absent."""
        try:
            return self._agents[name]
        except KeyError:
            raise ResourceUnavailableError(
                f"No agent definition named {name!r}. Known: {sorted(self._agents)}"
            ) from None


def _discover_and_register_phases(
    registry: PhaseRegistry,
    phases_dir: Path,
    import_prefix: str,
) -> None:
    """Import every non-private *.py in phases_dir and register Phase subclasses.

    Modules are imported by dotted path: ``{import_prefix}.{file_stem}``. The
    caller is responsible for choosing the right pair (dir, prefix). Import
    errors are fatal — a syntax error in any discovered module aborts startup.
    """
    for py_file in phases_dir.glob("*.py"):
        if py_file.stem.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{import_prefix}.{py_file.stem}")
        except Exception as e:
            raise FlowConfigError(f"Failed to import phase module '{py_file.stem}': {e}") from e
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Phase) and not inspect.isabstract(obj) and obj.__module__ == module.__name__:
                registry.register(obj.__name__, obj)


class PhaseOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        flow_yaml_path: Path,
        checkpoint_path: Path,
        runtime_variables: dict[str, str],
        agent_clients: dict[str, Any],
        file_access_policy: FileAccessPolicy,
        callbacks: Callbacks | None = None,
        grace_period: float = 10,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the orchestrator.

        ``agent_clients`` maps provider name (e.g. ``"anthropic"``) to a constructed
        provider client. ``build_agent`` looks up the right one based on each
        ``AgentConfig.provider``.

        ``file_access_policy`` must have ``write_root`` set to the integration
        output directory so that agent writes are confined to that path.
        """
        super().__init__(logger=logger or logging.getLogger(__name__), grace_period=grace_period)
        self._flow_yaml_path = flow_yaml_path
        self._checkpoint_path = checkpoint_path
        self._runtime_variables = runtime_variables
        self._agent_clients = agent_clients
        self._file_access_policy = file_access_policy
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._phase_registry = PhaseRegistry()
        self._failed_phase: str | None = None
        self._failed_error: str | None = None
        self._resources: ResourceProvider | None = None

    async def on_initialize(self) -> None:
        """Discover custom phases, parse flow.yaml, construct phases, submit PhaseTrigger."""
        config_dir = self._flow_yaml_path.parent

        _discover_and_register_phases(
            self._phase_registry,
            Path(__file__).parent,
            "ddev.ai.phases",
        )

        flow_phases_dir = config_dir / "phases"
        if flow_phases_dir.is_dir():
            ai_root = Path(__file__).parent.parent
            try:
                rel = flow_phases_dir.relative_to(ai_root)
            except ValueError:
                raise FlowConfigError(
                    f"Flow phases directory {flow_phases_dir} must be inside the ddev.ai package tree ({ai_root})"
                ) from None
            flow_import_prefix = "ddev.ai." + ".".join(rel.parts)
            _discover_and_register_phases(
                self._phase_registry,
                flow_phases_dir,
                flow_import_prefix,
            )

        config = FlowConfig.from_yaml(self._flow_yaml_path, config_dir)

        flow_phase_ids = {entry.phase for entry in config.flow}
        for phase_id, phase_config in config.phases.items():
            if phase_id not in flow_phase_ids:
                self._logger.warning("Phase %r is defined but not referenced in flow — it will not run", phase_id)
                continue
            try:
                phase_cls = self._phase_registry.get(phase_config.type)
            except ValueError as e:
                raise FlowConfigError(str(e)) from e
            phase_cls.validate_config(phase_id, phase_config, config.agents)

        checkpoint_manager = CheckpointManager(self._checkpoint_path)
        dependency_map: dict[str, list[str]] = {entry.phase: entry.dependencies for entry in config.flow}

        self._resources = ResourceProvider(
            agent_clients=self._agent_clients,
            file_access_policy=self._file_access_policy,
            agents=config.agents,
        )
        context = FlowContext(
            runtime_variables=self._runtime_variables,
            flow_variables=config.variables,
            config_dir=config_dir,
            callbacks=self._callbacks,
            logger=self._logger,
        )

        for entry in config.flow:
            phase_id = entry.phase
            phase_config = config.phases[phase_id]
            deps = dependency_map[phase_id]
            phase_cls = self._phase_registry.get(phase_config.type)
            phase = phase_cls.build(
                phase_id=phase_id,
                config=phase_config,
                deps=deps,
                resources=self._resources,
                checkpoint_manager=checkpoint_manager,
                context=context,
            )
            self.register_processor(phase, [PhaseTrigger])

        self.submit_message(PhaseTrigger(id="start", phase_id=None))

    async def on_message_received(self, message: BaseMessage) -> None:
        """Stop the entire pipeline immediately when any phase fails."""
        if isinstance(message, PhaseFailedMessage):
            self._failed_phase = message.phase_id
            self._failed_error = message.error
            raise FatalProcessingError(f"Phase '{message.phase_id}' failed: {message.error}")

    async def on_finalize(self, exception: Exception | None) -> None:
        if exception is not None and self._failed_phase is not None:
            self._logger.error(
                "Pipeline aborted: phase '%s' failed: %s",
                self._failed_phase,
                self._failed_error or "<unknown>",
            )
