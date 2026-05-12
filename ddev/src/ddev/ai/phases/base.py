# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, PhaseConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.event_bus.exceptions import MessageProcessingError, ProcessorHookError
from ddev.event_bus.orchestrator import AsyncProcessor, BaseMessage


@dataclass
class PhaseOutcome:
    memory_text: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    extra_checkpoint: dict[str, Any] = field(default_factory=dict)


class PhaseRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, type["Phase"]] = {}

    def register(self, name: str, phase_cls: type["Phase"]) -> None:
        self._registry[name] = phase_cls

    def known_names(self) -> list[str]:
        return sorted(self._registry)

    def get(self, name: str) -> type["Phase"]:
        if name not in self._registry:
            raise ValueError(f"Unknown phase type: {name!r}. Known: {self.known_names()}")
        return self._registry[name]


def _make_memory_resolver(checkpoint_manager: CheckpointManager) -> Callable[[str], str]:
    """Build a resolver that reads phase memory files on demand for template substitution."""

    def resolve(key: str) -> str:
        if key.endswith("_memory"):
            return checkpoint_manager.memory_content(key.removesuffix("_memory"))
        return f"<VARIABLE UNDEFINED: {key}>"

    return resolve


class Phase(AsyncProcessor[PhaseTrigger]):
    """Lifecycle base for all phases.

    process_message() implements the immutable pipeline skeleton.
    Subclasses implement execute() to provide phase-specific logic.
    Registered in PhaseRegistry by _discover_and_register_phases() at startup.
    """

    def __init__(
        self,
        phase_id: str,
        dependencies: list[str],
        config: PhaseConfig,
        checkpoint_manager: CheckpointManager,
        runtime_variables: dict[str, str],
        flow_variables: dict[str, str],
        config_dir: Path,
        file_registry: FileRegistry,
        callbacks: Callbacks | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(name=phase_id)
        self._phase_id = phase_id
        self._dependencies = set(dependencies)
        self._remaining_dependencies = set(dependencies)
        self._config = config
        self._checkpoint_manager = checkpoint_manager
        self._runtime_variables = runtime_variables
        self._flow_variables = flow_variables
        self._config_dir = config_dir
        self._callbacks: Callbacks = callbacks or Callbacks()
        self._file_registry = file_registry
        self._logger = logger or logging.getLogger(__name__)
        self._started_at: datetime | None = None
        self._resolver: Callable[[str], str] | None = None
        self._executed = False

    def should_process_message(self, message: BaseMessage) -> bool:
        if isinstance(message, PhaseTrigger):
            if message.phase_id is None:
                # Initial trigger — only root phases (no declared dependencies) respond
                if self._dependencies:
                    return False
            else:
                # Phase-completion trigger — check dependency tracking
                if message.phase_id not in self._dependencies:
                    return False
                self._remaining_dependencies.discard(message.phase_id)
                if self._remaining_dependencies:
                    return False
        if self._executed:
            return False
        self._executed = True
        return True

    @classmethod
    def validate_config(
        cls,
        phase_id: str,
        config: PhaseConfig,
        agents: dict[str, AgentConfig],
    ) -> None:
        """Override to enforce per-subclass config invariants. Raise FlowConfigError on mismatch."""
        return None

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
        self._resolver = _make_memory_resolver(self._checkpoint_manager)

        outcome = await self.execute(context)

        self._checkpoint_manager.write_memory(self._phase_id, outcome.memory_text)

        checkpoint_payload: dict[str, Any] = {
            "status": "success",
            "started_at": self._started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "tokens": {
                "total_input": outcome.total_input_tokens,
                "total_output": outcome.total_output_tokens,
            },
            "memory_path": str(self._checkpoint_manager.memory_path(self._phase_id)),
        }
        reserved = set(checkpoint_payload) & set(outcome.extra_checkpoint)
        if reserved:
            raise ValueError(
                f"Phase {self._phase_id!r}: extra_checkpoint cannot override reserved keys: {sorted(reserved)}"
            )
        checkpoint_payload.update(outcome.extra_checkpoint)

        self._checkpoint_manager.write_phase_checkpoint(self._phase_id, checkpoint_payload)
        await self._callbacks.fire_phase_finish(self._phase_id)

    async def on_success(self, message: PhaseTrigger) -> None:
        """Emit PhaseTrigger to unblock dependent phases."""
        self.submit_message(
            PhaseTrigger(
                id=f"{self._phase_id}_finished",
                phase_id=self._phase_id,
            )
        )

    async def on_error(self, error: MessageProcessingError | ProcessorHookError) -> None:
        """Write failed checkpoint and emit PhaseFailedMessage."""
        try:
            self._checkpoint_manager.write_phase_checkpoint(
                self._phase_id,
                {
                    "status": "failed",
                    "started_at": self._started_at.isoformat() if self._started_at else None,
                    "finished_at": datetime.now(UTC).isoformat(),
                    "error": str(error.original_exception),
                },
            )
        except Exception:
            self._logger.exception("Failed to write failure checkpoint for phase %s", self._phase_id)
        finally:
            self.submit_message(
                PhaseFailedMessage(
                    id=f"{self._phase_id}_failed",
                    phase_id=self._phase_id,
                    error=str(error.original_exception),
                )
            )
