# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, PhaseConfig, TaskConfig
from ddev.ai.phases.messages import PhaseFailedMessage, PhaseFinishedMessage, StartMessage
from ddev.ai.phases.template import render_inline, render_prompt
from ddev.ai.react.callbacks import CallbackSet
from ddev.ai.react.process import ReActProcess
from ddev.ai.tools.core.registry import ToolRegistry
from ddev.event_bus.orchestrator import AsyncProcessor


class PhaseRegistry:
    _registry: dict[str, type["Phase"]] = {}

    @classmethod
    def get(cls, name: str) -> type["Phase"]:
        if name not in cls._registry:
            raise ValueError(f"Unknown phase type: {name!r}. Known: {sorted(cls._registry)}")
        return cls._registry[name]


def _make_memory_resolver(checkpoint_manager: CheckpointManager) -> Callable[[str], str]:
    """Build a resolver that reads phase memory files on demand for template substitution."""

    def resolve(key: str) -> str:
        if key.endswith("_memory"):
            return checkpoint_manager.get_memory(key.removesuffix("_memory"))
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
    return render_inline(task.prompt, context, resolver)  # type: ignore[arg-type]


def render_memory_prompt(checkpoint: CheckpointConfig, config_dir: Path, context: dict[str, Any]) -> str:
    """Render a checkpoint memory prompt -- from file if memory_prompt_path is set, inline otherwise."""
    if checkpoint.memory_prompt_path is not None:
        return render_prompt(config_dir / checkpoint.memory_prompt_path, context)
    return render_inline(checkpoint.memory_prompt, context)  # type: ignore[arg-type]


class Phase(AsyncProcessor[StartMessage | PhaseFinishedMessage]):
    """Concrete base for all phases.

    process_message() implements the immutable pipeline skeleton.
    Override before_react(), after_react(), and run_tasks() to customize phase behaviour.
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
        callback_sets: list[CallbackSet] | None = None,
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
        self._callback_sets = callback_sets
        self._started_at: datetime | None = None
        self._resolver: Callable[[str], str] | None = None
        self._executed = False
        self._finish_emitted = False

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

    async def process_message(self, message: StartMessage | PhaseFinishedMessage) -> None:
        """Full phase pipeline. Not intended to be overridden -- customise via the extension points."""
        # 1. Relevance check (non-root phases only)
        if isinstance(message, PhaseFinishedMessage):
            if message.phase_id not in self._dependencies:
                return
            self._remaining_dependencies.discard(message.phase_id)
            if self._remaining_dependencies:
                return

        # 2. Guard against re-execution (remaining_dependencies is empty after first run,
        #    so later PhaseFinishedMessages for known deps would pass the check above)
        if self._executed:
            return
        self._executed = True

        # 3. Record start time
        self._started_at = datetime.now(UTC)

        # 3. Build template context and memory resolver
        context: dict[str, Any] = {
            **self._flow_variables,
            **self._runtime_variables,
            "phase_name": self._phase_id,
            "checkpoints": self._checkpoint_manager.read(),
        }
        self._resolver = _make_memory_resolver(self._checkpoint_manager)

        # 4. Call before_react()
        self.before_react()

        # 5. Create system prompt, ToolRegistry, AnthropicAgent
        system_prompt = render_prompt(
            self._config_dir / "prompts" / f"{self._config.agent}.md",
            context,
            self._resolver,
        )
        tool_registry = ToolRegistry.from_names(self._agent_config.tools)

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

        # 6. Build ReActProcess
        process = ReActProcess(
            agent=agent,
            tool_registry=tool_registry,
            callback_sets=self._callback_sets,
        )

        # 7. Call run_tasks()
        total_input, total_output = await self.run_tasks(process, context)

        # 8. Call after_react()
        self.after_react()

        # 9. Memory step (always)
        user_additions = None
        if self._config.checkpoint is not None:
            user_additions = render_memory_prompt(self._config.checkpoint, self._config_dir, context)

        prompt = self._checkpoint_manager.build_memory_prompt(user_additions)
        response = await agent.send(prompt)
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        self._checkpoint_manager.write_memory(self._phase_id, response.text)

        # 10. Write checkpoint
        self._checkpoint_manager.write_phase_checkpoint(
            self._phase_id,
            {
                "status": "success",
                "started_at": self._started_at.isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
                "tokens": {"total_input": total_input, "total_output": total_output},
            },
        )

    async def on_success(self, message: StartMessage | PhaseFinishedMessage) -> None:
        """Emit PhaseFinishedMessage to unblock dependent phases.

        Only emits once, and only after the phase actually executed. Early returns
        from process_message (irrelevant messages, already executed) also trigger
        on_success via _task_wrapper, but must not emit new messages.
        """
        if not self._executed or self._finish_emitted:
            return
        self._finish_emitted = True
        self.submit_message(
            PhaseFinishedMessage(
                id=f"{self._phase_id}_finished_{message.id}",
                phase_id=self._phase_id,
            )
        )

    async def on_error(self, message: StartMessage | PhaseFinishedMessage, error: Exception) -> None:
        """Write failed checkpoint and emit PhaseFailedMessage."""
        if self._finish_emitted:
            return
        self._finish_emitted = True
        self._checkpoint_manager.write_phase_checkpoint(
            self._phase_id,
            {
                "status": "failed",
                "started_at": self._started_at.isoformat() if self._started_at else None,
                "finished_at": datetime.now(UTC).isoformat(),
                "error": str(error),
            },
        )
        self.submit_message(
            PhaseFailedMessage(
                id=f"{self._phase_id}_failed_{message.id}",
                phase_id=self._phase_id,
                error=str(error),
            )
        )
