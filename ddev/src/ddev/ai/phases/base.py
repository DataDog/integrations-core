# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseTrigger
from ddev.ai.phases.template import render_inline, render_prompt
from ddev.ai.react.process import ReActProcess
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry
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


def render_task_prompt(
    task: TaskConfig,
    config_dir: Path,
    context: dict[str, Any],
    resolver: Callable[[str], str] | None = None,
) -> str:
    """Render a task prompt -- from file if prompt_path is set, inline otherwise."""
    if task.prompt_path is not None:
        return render_prompt(config_dir / task.prompt_path, context, resolver)
    if task.prompt is None:
        raise FlowConfigError("TaskConfig must set either 'prompt' or 'prompt_path'")
    return render_inline(task.prompt, context, resolver)


def render_memory_prompt(checkpoint: CheckpointConfig, config_dir: Path, context: dict[str, Any]) -> str:
    """Render a checkpoint memory prompt -- from file if memory_prompt_path is set, inline otherwise."""
    if checkpoint.memory_prompt_path is not None:
        return render_prompt(config_dir / checkpoint.memory_prompt_path, context)
    if checkpoint.memory_prompt is None:
        raise FlowConfigError("CheckpointConfig must set either 'memory_prompt' or 'memory_prompt_path'")
    return render_inline(checkpoint.memory_prompt, context)


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
        agent_config: AgentConfig,
        anthropic_client: anthropic.AsyncAnthropic,
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
        self._agent_config = agent_config
        self._anthropic_client = anthropic_client
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

    def before_react(self) -> None:
        """Called once before agent/tools are created. Override for phase-specific setup."""

    def after_react(self) -> None:
        """Called once after all tasks complete. Override for phase-specific teardown."""

    async def run_tasks(
        self,
        process: ReActProcess,
        context: dict[str, Any],
    ) -> tuple[int, int]:
        """Run the task loop. Returns (total_input_tokens, total_output_tokens).

        Override to customize task execution -- e.g. add retries, change ordering, etc.
        Default implementation iterates through config.tasks sequentially.
        """
        total_input = total_output = 0
        last_result = None
        for task in self._config.tasks:
            if last_result is not None and last_result.context_usage is not None:
                if last_result.context_usage.context_pct >= self._config.context_compact_threshold_pct:
                    compact_in, compact_out = await process.compact()
                    total_input += compact_in
                    total_output += compact_out
            prompt = render_task_prompt(task, self._config_dir, context, self._resolver)
            last_result = await process.start(prompt)
            total_input += last_result.total_input_tokens
            total_output += last_result.total_output_tokens
        return total_input, total_output

    async def execute(self, context: dict[str, Any]) -> PhaseOutcome:
        """Run the phase-specific logic and return a PhaseOutcome. Subclasses must override."""
        self.before_react()

        system_prompt = render_prompt(
            self._config_dir / "prompts" / f"{self._config.agent}.md",
            context,
            self._resolver,
        )
        tool_registry = ToolRegistry.from_names(
            self._agent_config.tools,
            owner_id=self._phase_id,
            file_registry=self._file_registry,
        )

        agent_kwargs: dict[str, Any] = {}
        if self._agent_config.model is not None:
            agent_kwargs["model"] = self._agent_config.model
        if self._agent_config.max_tokens is not None:
            agent_kwargs["max_tokens"] = self._agent_config.max_tokens

        agent = AnthropicAgent(
            client=self._anthropic_client,
            tools=tool_registry,
            system_prompt=system_prompt,
            name=self._phase_id,
            **agent_kwargs,
        )

        process = ReActProcess(
            agent=agent,
            tool_registry=tool_registry,
            callbacks=self._callbacks,
        )

        total_input, total_output = await self.run_tasks(process, context)

        self.after_react()

        user_additions = None
        if self._config.checkpoint is not None:
            user_additions = render_memory_prompt(self._config.checkpoint, self._config_dir, context)
        memory_prompt = self._checkpoint_manager.build_memory_prompt(user_additions)

        await self._callbacks.fire_before_agent_send(1)
        response = await agent.send(memory_prompt, allowed_tools=[])
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        await self._callbacks.fire_agent_response(response, 1)

        return PhaseOutcome(
            memory_text=response.text,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
        )

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
