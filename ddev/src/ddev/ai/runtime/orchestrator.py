# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from pathlib import Path
from typing import Any

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.engine import ConfigurationEngine
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.registry import PhaseRegistry
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator


class PhaseOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        engine: ConfigurationEngine,
        phase_registry: PhaseRegistry,
        flow_name: str,
        checkpoint_path: Path,
        runtime_variables: dict[str, str],
        agent_clients: dict[str, Any],
        file_access_policy: FileAccessPolicy,
        callbacks: Callbacks | None = None,
        grace_period: float = 10,
        max_timeout: float = 600,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the orchestrator.

        ``engine`` is a pre-built ``ConfigurationEngine`` that has already validated every
        flow and inlined all prompt/goal/memory references. ``phase_registry`` is the same
        registry the engine validated against, pre-populated by the composition root.

        ``agent_clients`` maps provider name (e.g. ``"anthropic"``) to a constructed
        provider client. ``DefaultAgentRuntimeFactory`` resolves the right one based on each
        ``AgentConfig.provider``.

        ``file_access_policy`` must have ``write_root`` set to the integration
        output directory so that agent writes are confined to that path.

        ``max_timeout`` is the maximum time in seconds to wait for the whole run of the
        orchestrator to complete.
        """
        super().__init__(
            logger=logger or logging.getLogger(__name__),
            grace_period=grace_period,
            max_timeout=max_timeout,
        )
        self._engine = engine
        self._phase_registry = phase_registry
        self._flow_name = flow_name
        self._checkpoint_path = checkpoint_path
        self._runtime_variables = runtime_variables
        self._agent_clients = agent_clients
        self._file_access_policy = file_access_policy
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._agent_logger: AgentLogger | None = None
        self._failed_phase: str | None = None
        self._failed_error: str | None = None

    async def on_initialize(self) -> None:
        """Resolve the flow from the engine, construct phases, submit the start PhaseTrigger."""
        resolved = self._engine.get_flow(self._flow_name)

        checkpoint_manager = CheckpointManager(self._checkpoint_path)
        self._agent_logger = AgentLogger(checkpoint_manager.root)
        run_callbacks = self._callbacks.with_set(self._agent_logger.as_callback_set())

        self._resources = RunResources(
            agent_clients=self._agent_clients,
            file_access_policy=self._file_access_policy,
            agents=resolved.agents,
            callbacks=run_callbacks,
            prompts=resolved.prompts,
            goals=resolved.goals,
            memories=resolved.memories,
        )
        context = FlowContext(
            runtime_variables=self._runtime_variables,
            flow_variables=resolved.variables,
            callbacks=run_callbacks,
            logger=self._logger,
        )

        dependency_map: dict[str, list[str]] = {entry.phase: entry.dependencies for entry in resolved.flow}
        for entry in resolved.flow:
            phase_config = resolved.phases[entry.phase]
            phase = self._phase_registry.get(phase_config.class_).build(
                phase_id=entry.phase,
                config=phase_config,
                deps=dependency_map[entry.phase],
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
        if self._agent_logger is not None:
            self._agent_logger.close()
        if exception is not None and self._failed_phase is not None:
            self._logger.error(
                "Pipeline aborted: phase '%s' failed: %s",
                self._failed_phase,
                self._failed_error or "<unknown>",
            )
