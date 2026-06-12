# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from pathlib import Path
from typing import Any

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.config import FlowConfigError
from ddev.ai.phases.messages import PhaseFailedMessage
from ddev.ai.phases.registry import PhaseRegistry
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
        """Stub pending migration to ConfigurationEngine (Task 5)."""
        raise FlowConfigError("PhaseOrchestrator.on_initialize requires migration to ConfigurationEngine (Task 5)")

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
