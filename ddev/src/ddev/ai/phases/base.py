# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import logging
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import PhaseConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.runtime.checkpoints import (
    CheckpointManager,
    CheckpointTokenInfo,
    FailedCheckpoint,
    GoalValidationRecord,
    SuccessCheckpoint,
)
from ddev.event_bus.exceptions import MessageProcessingError, ProcessorHookError
from ddev.event_bus.orchestrator import AsyncProcessor, BaseMessage

if TYPE_CHECKING:
    from ddev.ai.phases.resources import PhaseResources


@dataclass(frozen=True)
class FlowContext:
    """Ambient, flow-scoped execution context shared by every phase."""

    runtime_variables: dict[str, str]
    flow_variables: dict[str, str]
    callbacks: Callbacks = field(default_factory=Callbacks)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    resume_frontier: frozenset[str] = frozenset()


@dataclass
class PhaseOutcome:
    memory_text: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    goal_validations: list[GoalValidationRecord] | None = None
    checkpoint_data: dict[str, Any] = field(default_factory=dict)


class Phase(AsyncProcessor[PhaseTrigger]):
    """Lifecycle base for all phases.

    process_message() implements the immutable pipeline skeleton.
    Subclasses implement execute() to provide phase-specific logic.
    """

    def __init__(
        self,
        phase_id: str,
        dependencies: list[str],
        config: PhaseConfig,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
    ) -> None:
        super().__init__(name=phase_id)
        self._phase_id = phase_id
        self._remaining_dependencies = set(dependencies)
        self._config = config
        self._checkpoint_manager = checkpoint_manager
        self._runtime_variables = context.runtime_variables
        self._flow_variables = context.flow_variables
        self._callbacks = context.callbacks
        self._logger = context.logger
        self._is_resume_frontier = phase_id in context.resume_frontier
        self._started_at: datetime | None = None
        self._resolver: Callable[[str], str] | None = None
        self._executed = False

    def should_process_message(self, message: BaseMessage) -> bool:
        if isinstance(message, PhaseTrigger):
            if message.phase_id is None:
                # Initial trigger — only root phases (no declared dependencies) respond
                if self._remaining_dependencies:
                    return False
            else:
                # Phase-completion trigger — check dependency tracking
                if message.phase_id not in self._remaining_dependencies:
                    return False
                self._remaining_dependencies.discard(message.phase_id)
                if self._remaining_dependencies:
                    return False
        if self._executed:
            return False
        self._executed = True
        return True

    @classmethod
    def validate_config(cls, phase_id: str, config: PhaseConfig) -> None:
        """Override to enforce per-subclass config invariants. Raise ConfigError on mismatch."""
        return None

    @classmethod
    def build(
        cls,
        phase_id: str,
        config: PhaseConfig,
        deps: list[str],
        resources: PhaseResources,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
    ) -> Phase:
        """Uniform polymorphic factory called by the orchestrator for every phase.

        Subclasses that need infrastructure (agent builders, file registry)
        pull it from ``resources`` inside their own ``build()`` override.
        """
        return cls(
            phase_id=phase_id,
            dependencies=deps,
            config=config,
            checkpoint_manager=checkpoint_manager,
            context=context,
        )

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> PhaseOutcome: ...

    async def process_message(self, message: PhaseTrigger) -> None:
        """Immutable pipeline skeleton. Not intended to be overridden — implement execute() instead."""
        self._started_at = datetime.now(UTC)
        await self._callbacks.fire_phase_start(self._phase_id)

        context: dict[str, Any] = {
            **self._flow_variables,
            **self._runtime_variables,
            "phase_name": self._phase_id,
            "checkpoints": self._checkpoint_manager.read(),
        }
        self._resolver = self._checkpoint_manager.resolve_template_variable

        outcome = await self.execute(context)

        checkpoint = SuccessCheckpoint(
            started_at=self._started_at.isoformat(),
            finished_at=datetime.now(UTC).isoformat(),
            tokens=CheckpointTokenInfo(
                total_input=outcome.total_input_tokens,
                total_output=outcome.total_output_tokens,
            ),
            memory_path=str(self._checkpoint_manager.memory_path(self._phase_id)),
            goal_validations=outcome.goal_validations,
            phase_data=outcome.checkpoint_data,
        )

        self._checkpoint_manager.write_memory(self._phase_id, outcome.memory_text)
        self._checkpoint_manager.write_phase_checkpoint(self._phase_id, checkpoint)
        await self._callbacks.fire_phase_finish(self._phase_id)

    async def on_success(self, message: PhaseTrigger) -> None:
        """Emit PhaseTrigger to unblock dependent phases."""
        self.submit_message(
            PhaseTrigger(
                id=f"{self._phase_id}_finished",
                phase_id=self._phase_id,
            )
        )

    def build_failed_checkpoint(self, error: BaseException) -> FailedCheckpoint:
        """Build the checkpoint persisted when this phase fails."""
        return FailedCheckpoint(
            started_at=self._started_at.isoformat() if self._started_at else None,
            finished_at=datetime.now(UTC).isoformat(),
            error=str(error),
            tokens=CheckpointTokenInfo(total_input=0, total_output=0),
        )

    async def on_error(self, error: MessageProcessingError | ProcessorHookError) -> None:
        """Persist and publish a phase failure."""
        original_error = error.original_exception
        try:
            self._checkpoint_manager.write_phase_checkpoint(
                self._phase_id,
                self.build_failed_checkpoint(original_error),
            )
        except Exception:
            self._logger.exception("Failed to write failure checkpoint for phase %s", self._phase_id)
        finally:
            await self._callbacks.fire_phase_error(self._phase_id, original_error)
            self.submit_message(
                PhaseFailedMessage(
                    id=f"{self._phase_id}_failed",
                    phase_id=self._phase_id,
                    error=str(original_error),
                )
            )
