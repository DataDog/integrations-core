# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import importlib
import inspect
import logging
from pathlib import Path
from typing import Any

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.base import Phase, PhaseRegistry
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import FlowConfig, FlowConfigError
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator


def _discover_and_register_phases(
    registry: PhaseRegistry,
    phases_dir: Path | None = None,
    import_prefix: str = "ddev.ai.phases",
) -> None:
    """Import all non-private modules in phases_dir and register Phase subclasses."""
    if phases_dir is None:
        phases_dir = Path(__file__).parent
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
        max_timeout: float = 300,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the orchestrator.

        ``agent_clients`` maps provider name (e.g. ``"anthropic"``) to a constructed
        provider client. ``build_agent`` looks up the right one based on each
        ``AgentConfig.provider``.

        ``file_access_policy`` must have ``write_root`` set to the integration
        output directory so that agent writes are confined to that path.
        """
        super().__init__(
            logger=logger or logging.getLogger(__name__), grace_period=grace_period, max_timeout=max_timeout
        )
        self._flow_yaml_path = flow_yaml_path
        self._checkpoint_path = checkpoint_path
        self._runtime_variables = runtime_variables
        self._agent_clients = agent_clients
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._phase_registry = PhaseRegistry()
        self._failed_phase: str | None = None
        self._failed_error: str | None = None
        self._file_registry = FileRegistry(policy=file_access_policy)

    async def on_initialize(self) -> None:
        """Discover custom phases, parse flow.yaml, construct phases, submit PhaseTrigger."""
        config_dir = self._flow_yaml_path.parent

        _discover_and_register_phases(self._phase_registry)

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

        for entry in config.flow:
            phase_id = entry.phase
            phase_config = config.phases[phase_id]
            dependencies = dependency_map[phase_id]

            phase_cls = self._phase_registry.get(phase_config.type)
            phase_kwargs: dict[str, Any] = {
                "phase_id": phase_id,
                "dependencies": dependencies,
                "config": phase_config,
                "checkpoint_manager": checkpoint_manager,
                "runtime_variables": self._runtime_variables,
                "flow_variables": config.variables,
                "config_dir": config_dir,
                "file_registry": self._file_registry,
                "callbacks": self._callbacks,
                "logger": self._logger,
            }
            phase_kwargs.update(
                phase_cls.extra_init_kwargs(
                    phase_id=phase_id,
                    phase_config=phase_config,
                    agents=config.agents,
                    agent_clients=self._agent_clients,
                    file_registry=self._file_registry,
                )
            )

            phase = phase_cls(**phase_kwargs)

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
