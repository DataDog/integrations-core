# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import sys
from pathlib import Path
from typing import Any

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.engine import CORE_PHASES_DIR, ConfigurationEngine
from ddev.ai.config.errors import FlowConfigError
from ddev.ai.config.models import ResolvedFlow
from ddev.ai.phases.base import FlowContext
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.registry import PhaseRegistry, discover_and_register_phases
from ddev.ai.runtime.agent_log import AgentLogger
from ddev.ai.runtime.checkpoints import CheckpointManager
from ddev.ai.runtime.resources import RunResources
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator


def _import_prefix_from_path(path: Path) -> str:
    """Derive the dotted import prefix for path from sys.path entries."""
    resolved = path.resolve()
    for entry in sys.path:
        if not entry:
            continue
        root = Path(entry).resolve()
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            continue
        return ".".join(rel.parts)
    raise RuntimeError(f"Could not derive import prefix for {path}")


class PhaseOrchestrator(EventBusOrchestrator):
    def __init__(
        self,
        engine: ConfigurationEngine,
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
        self._engine = engine
        self._checkpoint_path = checkpoint_path
        self._runtime_variables = runtime_variables
        self._agent_clients = agent_clients
        self._file_access_policy = file_access_policy
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._agent_logger: AgentLogger | None = None
        self._resources: RunResources | None = None
        self._phase_registry = PhaseRegistry()
        self._failed_phase: str | None = None
        self._failed_error: str | None = None

    async def on_initialize(self) -> None:
        self._discover_phases()
        resolved = self._engine.build_flow()
        self._validate_phase_classes(resolved)
        self._agent_logger, self._resources, checkpoint_manager, context = self._build_runtime(resolved)
        self._register_phases(resolved, self._resources, checkpoint_manager, context)
        self.submit_message(PhaseTrigger(id="start", phase_id=None))

    def _discover_phases(self) -> None:
        for phases_dir, import_prefix in self._phase_discovery_targets():
            discover_and_register_phases(self._phase_registry, phases_dir, import_prefix)

    def _phase_discovery_targets(self) -> list[tuple[Path, str]]:
        targets: list[tuple[Path, str]] = []
        seen: set[Path] = set()

        if CORE_PHASES_DIR.is_dir():
            try:
                prefix = _import_prefix_from_path(CORE_PHASES_DIR)
                seen.add(CORE_PHASES_DIR.resolve())
                targets.append((CORE_PHASES_DIR, prefix))
            except RuntimeError:
                self._logger.warning(
                    "CORE_PHASES_DIR %s is not under any sys.path entry — core phase classes will be unavailable",
                    CORE_PHASES_DIR,
                )

        for scan_dir in self._engine.scan_dirs:
            for phases_dir in scan_dir.rglob("phases"):
                if not phases_dir.is_dir():
                    continue
                resolved = phases_dir.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                try:
                    prefix = _import_prefix_from_path(phases_dir)
                    targets.append((phases_dir, prefix))
                except RuntimeError:
                    self._logger.warning(
                        "phases/ directory %s is not under any sys.path entry — "
                        "its phase classes cannot be auto-imported and will be unavailable at runtime",
                        phases_dir,
                    )
        return targets

    def _validate_phase_classes(self, resolved: ResolvedFlow) -> None:
        for phase_id, phase_config in resolved.phases.items():
            try:
                phase_cls = self._phase_registry.get(phase_config.class_)
            except ValueError as e:
                raise FlowConfigError(f"Phase {phase_id!r} declares unknown class {phase_config.class_!r}: {e}") from e
            phase_cls.validate_config(phase_id, phase_config, resolved.agents)

    def _build_runtime(
        self, resolved: ResolvedFlow
    ) -> tuple[AgentLogger, RunResources, CheckpointManager, FlowContext]:
        checkpoint_manager = CheckpointManager(self._checkpoint_path)
        agent_logger = AgentLogger(checkpoint_manager.root)
        run_callbacks = self._callbacks.with_set(agent_logger.as_callback_set())
        resources = RunResources(
            agent_clients=self._agent_clients,
            file_access_policy=self._file_access_policy,
            agents=resolved.agents,
            callbacks=run_callbacks,
        )
        context = FlowContext(
            runtime_variables=self._runtime_variables,
            flow_variables=resolved.variables,
            callbacks=run_callbacks,
            logger=self._logger,
        )
        return agent_logger, resources, checkpoint_manager, context

    def _register_phases(
        self,
        resolved: ResolvedFlow,
        resources: RunResources,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
    ) -> None:
        dependency_map = {entry.phase: entry.dependencies for entry in resolved.flow}
        for entry in resolved.flow:
            phase_id = entry.phase
            phase_config = resolved.phases[phase_id]
            deps = dependency_map[phase_id]
            phase_cls = self._phase_registry.get(phase_config.class_)
            phase = phase_cls.build(
                phase_id=phase_id,
                config=phase_config,
                deps=deps,
                resources=resources,
                checkpoint_manager=checkpoint_manager,
                context=context,
            )
            self.register_processor(phase, [PhaseTrigger])

    async def on_message_received(self, message: BaseMessage) -> None:
        """Stop the entire pipeline immediately when any phase fails."""
        if isinstance(message, PhaseFailedMessage):
            self._failed_phase = message.phase_id
            self._failed_error = message.error
            raise FatalProcessingError(f"Phase '{message.phase_id}' failed: {message.error}")

    async def on_finalize(self, exception: Exception | None) -> None:
        if self._agent_logger is not None:
            try:
                self._agent_logger.close()
            except Exception:
                self._logger.exception("Error closing agent logger during finalize")
        if exception is not None and self._failed_phase is not None:
            self._logger.error(
                "Pipeline aborted: phase '%s' failed: %s",
                self._failed_phase,
                self._failed_error or "<unknown>",
            )
