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
from ddev.ai.phases.config import FlowConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseFinishedMessage, StartMessage
from ddev.ai.react.callbacks import CallbackSet
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator


def _discover_and_register_phases() -> None:
    """Import every non-private module in ddev/ai/phases/ and register Phase subclasses.

    Phase itself is registered here too -- issubclass(Phase, Phase) is True and
    Phase.__module__ matches when base.py is processed.
    Framework modules are already in sys.modules; importlib.import_module is a no-op for them.
    Only custom phase files that haven't been imported yet trigger a real import.
    Non-phase files in phases/ must be prefixed with _ to be skipped.
    """
    phases_dir = Path(__file__).parent
    for py_file in phases_dir.glob("*.py"):
        if py_file.stem.startswith("_"):
            continue
        module = importlib.import_module(f"ddev.ai.phases.{py_file.stem}")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Phase) and obj.__module__ == module.__name__:
                PhaseRegistry._registry[obj.__name__] = obj


class PhaseOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        flow_yaml_path: Path,
        checkpoint_path: Path,
        runtime_variables: dict[str, str],
        anthropic_client: anthropic.AsyncAnthropic,
        callback_sets: list[CallbackSet] | None = None,
        grace_period: float = 10,
    ) -> None:
        super().__init__(logger=logging.getLogger(__name__), grace_period=grace_period)
        self._flow_yaml_path = flow_yaml_path
        self._checkpoint_path = checkpoint_path
        self._runtime_variables = runtime_variables
        self._anthropic_client = anthropic_client
        self._callback_sets = callback_sets

    async def on_initialize(self) -> None:
        """Discover custom phases, parse flow.yaml, construct phases, submit StartMessage."""
        config_dir = self._flow_yaml_path.parent

        _discover_and_register_phases()

        config = FlowConfig.from_yaml(self._flow_yaml_path, config_dir)

        checkpoint_manager = CheckpointManager(self._checkpoint_path)

        dependency_map: dict[str, list[str]] = {entry.phase: entry.dependencies for entry in config.flow}

        for entry in config.flow:
            phase_id = entry.phase
            phase_config = config.phases[phase_id]
            agent_config = config.agents[phase_config.agent]
            dependencies = dependency_map[phase_id]

            phase_cls = PhaseRegistry.get(phase_config.type)
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
            )

            if not dependencies:
                self.register_processor(phase, [StartMessage])
            else:
                self.register_processor(phase, [PhaseFinishedMessage])

        self.submit_message(StartMessage(id="start"))

    async def on_message_received(self, message: BaseMessage) -> None:
        """Stop the entire pipeline immediately when any phase fails."""
        if isinstance(message, PhaseFailedMessage):
            raise FatalProcessingError(f"Phase '{message.phase_id}' failed: {message.error}")

    async def on_finalize(self, exception: Exception | None) -> None:
        pass
