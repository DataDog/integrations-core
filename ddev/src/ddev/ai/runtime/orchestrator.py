# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from pathlib import Path
from typing import Any

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.config import FlowConfig, FlowConfigError
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.registry import PhaseRegistry, discover_and_register_phases
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator


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
        max_timeout: float = 600,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the orchestrator.

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
        self._flow_yaml_path = flow_yaml_path
        self._checkpoint_path = checkpoint_path
        self._runtime_variables = runtime_variables
        self._agent_clients = agent_clients
        self._file_access_policy = file_access_policy
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._agent_logger: AgentLogger | None = None
        self._phase_registry = PhaseRegistry()
        self._failed_phase: str | None = None
        self._failed_error: str | None = None

    async def on_initialize(self) -> None:
        """Discover custom phases, parse flow.yaml, construct phases, submit PhaseTrigger."""
        config_dir = self._flow_yaml_path.parent

        discover_and_register_phases(
            self._phase_registry,
            Path(__file__).parent.parent / "phases",
            "ddev.ai.phases",
        )

        flow_phases_dir = config_dir / "phases"
        if flow_phases_dir.is_dir():
            ai_root = Path(__file__).parent.parent
            try:
                rel = flow_phases_dir.relative_to(ai_root)
            except ValueError as e:
                raise FlowConfigError(
                    f"Flow phases directory {flow_phases_dir} must be inside the ddev.ai package tree ({ai_root})"
                ) from e
            flow_import_prefix = "ddev.ai." + ".".join(rel.parts)
            discover_and_register_phases(
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

        self._agent_logger = AgentLogger(checkpoint_manager.root)
        run_callbacks = self._callbacks.with_set(self._agent_logger.as_callback_set())

        self._resources = RunResources(
            agent_clients=self._agent_clients,
            file_access_policy=self._file_access_policy,
            agents=config.agents,
            callbacks=run_callbacks,
        )
        context = FlowContext(
            runtime_variables=self._runtime_variables,
            flow_variables=config.variables,
            config_dir=config_dir,
            callbacks=run_callbacks,
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
        if self._agent_logger is not None:
            self._agent_logger.close()
        if exception is not None and self._failed_phase is not None:
            self._logger.error(
                "Pipeline aborted: phase '%s' failed: %s",
                self._failed_phase,
                self._failed_error or "<unknown>",
            )
