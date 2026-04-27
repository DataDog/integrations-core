# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import importlib
import inspect
import logging
from pathlib import Path

import anthropic

from ddev.ai.phases.base import Phase, PhaseRegistry
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import FlowConfig, FlowConfigError
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.react.callbacks import CallbackSet
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
            if issubclass(obj, Phase) and obj.__module__ == module.__name__:
                registry.register(obj.__name__, obj)


class PhaseOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        flow_yaml_path: Path,
        checkpoint_path: Path,
        runtime_variables: dict[str, str],
        anthropic_client: anthropic.AsyncAnthropic,
        callback_sets: list[CallbackSet] | None = None,
        grace_period: float = 10,
        file_access_policy: FileAccessPolicy | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Production callers (e.g. the CLI) must pass a ``file_access_policy``
        with ``write_root`` set to the integration output directory so that
        agent writes are confined to that path. Passing ``None`` leaves writes
        unrestricted (appropriate only in tests).
        """
        super().__init__(logger=logging.getLogger(__name__), grace_period=grace_period)
        self._flow_yaml_path = flow_yaml_path
        self._checkpoint_path = checkpoint_path
        self._runtime_variables = runtime_variables
        self._anthropic_client = anthropic_client
        self._callback_sets = callback_sets
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
                self._phase_registry.get(phase_config.type)
            except ValueError as e:
                raise FlowConfigError(str(e)) from e

        checkpoint_manager = CheckpointManager(self._checkpoint_path)

        dependency_map: dict[str, list[str]] = {entry.phase: entry.dependencies for entry in config.flow}

        for entry in config.flow:
            phase_id = entry.phase
            phase_config = config.phases[phase_id]
            agent_config = config.agents[phase_config.agent]
            dependencies = dependency_map[phase_id]

            phase_cls = self._phase_registry.get(phase_config.type)
            phase = phase_cls(
                phase_id=phase_id,
                dependencies=dependencies,
                config=phase_config,
                agent_config=agent_config,
                anthropic_client=self._anthropic_client,
                checkpoint_manager=checkpoint_manager,
                runtime_variables=self._runtime_variables,
                flow_variables=config.variables,
                config_dir=config_dir,
                callback_sets=self._callback_sets,
                file_registry=self._file_registry,
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
        if self._failed_phase is not None:
            raise RuntimeError(
                f"Pipeline aborted: phase '{self._failed_phase}' failed: {self._failed_error or '<unknown>'}"
            )
