# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from pathlib import Path

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import ResolvedFlow
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.registry import PhaseRegistry
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.runtime.checkpoints import CheckpointManager, resolve_resume_state
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError, OrchestratorHookError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator

DEFAULT_GRACE_PERIOD = 10.0


class PhaseOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        resolved_flow: ResolvedFlow,
        phase_registry: PhaseRegistry,
        checkpoint_path: Path,
        runtime_variables: dict[str, str],
        provider_registry: AgentProviderRegistry,
        file_access_policy: FileAccessPolicy,
        callbacks: Callbacks | None = None,
        resume: bool = False,
        grace_period: float = DEFAULT_GRACE_PERIOD,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the orchestrator.

        ``resolved_flow`` is a fully validated, reference-inlined flow obtained from
        ``engine.get_flow(name)``. ``phase_registry`` is the same registry the engine
        validated against, used to instantiate phase classes.

        ``provider_registry`` is the same configured registry used to validate agent
        definitions and constructs provider-specific agents on demand.

        ``file_access_policy`` must have ``write_root`` set to the integration
        output directory so that agent writes are confined to that path.

        """
        max_timeout = runtime_variables.get("max_timeout")
        super().__init__(
            logger=logger or logging.getLogger(__name__),
            grace_period=grace_period,
            max_timeout=float(max_timeout) if max_timeout is not None else None,
        )
        self._resolved_flow = resolved_flow
        self._phase_registry = phase_registry
        self._checkpoint_path = checkpoint_path
        self._runtime_variables = runtime_variables
        self._provider_registry = provider_registry
        self._file_access_policy = file_access_policy
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._resume = resume
        self._agent_logger: AgentLogger | None = None
        self._failed_phase: str | None = None
        self._failed_error: str | None = None

    @property
    def failed_phase(self) -> str | None:
        return self._failed_phase

    async def on_initialize(self) -> None:
        """Construct phases from the resolved flow and submit the start PhaseTrigger."""
        checkpoint_manager = CheckpointManager(self._checkpoint_path)
        dependency_map: dict[str, list[str]] = {entry.phase: entry.dependencies for entry in self._resolved_flow.flow}

        completed, frontier = (
            resolve_resume_state(self._resolved_flow, checkpoint_manager) if self._resume else (set(), set())
        )
        if self._resume:
            self._logger.info(
                "Resuming: %d phase(s) completed, re-running frontier %r", len(completed), sorted(frontier)
            )

        self._agent_logger = AgentLogger(checkpoint_manager.root)
        run_callbacks = self._callbacks.with_set(self._agent_logger.as_callback_set())

        self._resources = RunResources(
            provider_registry=self._provider_registry,
            file_access_policy=self._file_access_policy,
            agents=self._resolved_flow.agents,
            callbacks=run_callbacks,
        )
        context = FlowContext(
            runtime_variables=self._runtime_variables,
            flow_variables=self._resolved_flow.variables,
            callbacks=run_callbacks,
            logger=self._logger,
            resume_frontier=frozenset(frontier),
        )

        for entry in self._resolved_flow.flow:
            if entry.phase in completed:
                self._logger.info("Resuming: skipping already-completed phase %r", entry.phase)
                continue
            phase_config = self._resolved_flow.phases[entry.phase]
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
        for entry in self._resolved_flow.flow:
            if entry.phase in completed:
                self.submit_message(PhaseTrigger(id=f"{entry.phase}_resumed", phase_id=entry.phase))

    async def on_message_received(self, message: BaseMessage) -> None:
        """Stop the entire pipeline immediately when any phase fails."""
        if isinstance(message, PhaseFailedMessage):
            self._failed_phase = message.phase_id
            self._failed_error = message.error
            error = FatalProcessingError(f"Phase '{message.phase_id}' failed: {message.error}")
            await self._callbacks.fire_run_error()
            raise error

    async def on_error(self, error: OrchestratorHookError) -> None:
        """Stop the run after an unexpected orchestrator failure."""
        raise FatalProcessingError(str(error)) from error.original_exception

    async def on_finalize(self, exception: Exception | None) -> None:
        if self._agent_logger is not None:
            self._agent_logger.close()
        if exception is not None and self._failed_phase is not None:
            self._logger.error(
                "Pipeline aborted: phase '%s' failed: %s",
                self._failed_phase,
                self._failed_error or "<unknown>",
            )
