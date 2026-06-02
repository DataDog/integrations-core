# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ddev.ai.phases.base import FlowContext, Phase, PhaseOutcome
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.goal import GOAL_TASK_SUFFIX, GoalValidationError, render_goal_text, run_goal_loop
from ddev.ai.phases.messages import PhaseFailedMessage
from ddev.ai.phases.template import render_inline, render_prompt
from ddev.ai.react.process import ReActProcess
from ddev.event_bus.exceptions import MessageProcessingError, ProcessorHookError

if TYPE_CHECKING:
    from ddev.ai.agent.base import BaseAgent
    from ddev.ai.agent.build import AgentRuntimeFactory
    from ddev.ai.phases.goal import GoalLoopOutcome
    from ddev.ai.phases.orchestrator import ResourceProvider
    from ddev.ai.react.types import ReActResult


def render_task_prompt(
    task: TaskConfig,
    config_dir: Path,
    context: dict[str, Any],
    resolver: Callable[[str], str] | None = None,
) -> str:
    """Render a task prompt — from file if prompt_path is set, inline otherwise."""
    if task.prompt_path is not None:
        return render_prompt(config_dir / task.prompt_path, context, resolver)
    if task.prompt is None:
        raise FlowConfigError("TaskConfig must set either 'prompt' or 'prompt_path'")
    return render_inline(task.prompt, context, resolver)


def render_memory_prompt(
    checkpoint: CheckpointConfig,
    config_dir: Path,
    context: dict[str, Any],
) -> str:
    """Render a checkpoint memory prompt — from file if memory_prompt_path is set, inline otherwise."""
    if checkpoint.memory_prompt_path is not None:
        return render_prompt(config_dir / checkpoint.memory_prompt_path, context)
    if checkpoint.memory_prompt is None:
        raise FlowConfigError("CheckpointConfig must set either 'memory_prompt' or 'memory_prompt_path'")
    return render_inline(checkpoint.memory_prompt, context)


class AgenticPhase(Phase):
    """Phase that owns an LLM agent and drives one or more ReAct loops."""

    def __init__(
        self,
        phase_id: str,
        dependencies: list[str],
        config: PhaseConfig,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
        agent_config: AgentConfig,
        runtime_factory: AgentRuntimeFactory,
    ) -> None:
        super().__init__(
            phase_id=phase_id,
            dependencies=dependencies,
            config=config,
            checkpoint_manager=checkpoint_manager,
            context=context,
        )
        self._agent_name = cast(str, config.agent)
        self._agent_config = agent_config
        self._runtime_factory = runtime_factory
        self._goal_attempt_log: list[dict[str, Any]] = []
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0

    @classmethod
    def validate_config(
        cls,
        phase_id: str,
        config: PhaseConfig,
        agents: dict[str, AgentConfig],
    ) -> None:
        if config.agent is None:
            raise FlowConfigError(f"Phase {phase_id!r} (AgenticPhase) requires 'agent'")
        if config.agent not in agents:
            raise FlowConfigError(f"Phase {phase_id!r} references unknown agent: {config.agent!r}")
        if not config.tasks:
            raise FlowConfigError(f"Phase {phase_id!r} (AgenticPhase) must have at least one task")

    @classmethod
    def build(
        cls,
        phase_id: str,
        config: PhaseConfig,
        deps: list[str],
        resources: ResourceProvider,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
    ) -> AgenticPhase:
        # config.agent is guaranteed set & known by validate_config.
        agent_name = cast(str, config.agent)
        agent_config = resources.agent_config(agent_name)
        runtime_factory = resources.agent_runtime_factory()

        return cls(
            phase_id=phase_id,
            dependencies=deps,
            config=config,
            checkpoint_manager=checkpoint_manager,
            context=context,
            agent_config=agent_config,
            runtime_factory=runtime_factory,
        )

    def before_react(self) -> None:
        """Called once before agent/tools are created. Override for phase-specific setup."""

    def after_react(self) -> None:
        """Called once after all tasks complete. Override for phase-specific teardown."""

    async def _compact_if_needed(
        self,
        process: ReActProcess,
        last_result: ReActResult | None,
    ) -> tuple[int, int]:
        if last_result is None or last_result.context_usage is None:
            return 0, 0
        if last_result.context_usage.context_pct < self._config.context_compact_threshold_pct:
            return 0, 0
        return await process.compact()

    async def run_tasks(
        self,
        process: ReActProcess,
        context: dict[str, Any],
    ) -> None:
        """Run the task loop, accumulating tokens into self._total_input/output_tokens.

        Override to customize task execution — e.g. add retries, change ordering, etc.
        Default implementation iterates through config.tasks sequentially.
        """
        last_result: ReActResult | None = None

        for task in self._config.tasks:
            cin, cout = await self._compact_if_needed(process, last_result)
            self._total_input_tokens += cin
            self._total_output_tokens += cout

            has_goal = task.goal is not None or task.goal_path is not None
            prompt = render_task_prompt(task, self._config_dir, context, self._resolver)
            if has_goal:
                prompt = prompt + GOAL_TASK_SUFFIX

            last_result = await process.start(prompt)
            self._total_input_tokens += last_result.total_input_tokens
            self._total_output_tokens += last_result.total_output_tokens

            if has_goal:
                goal_text = render_goal_text(task, self._config_dir, context, self._resolver)
                try:
                    outcome: GoalLoopOutcome = await run_goal_loop(
                        task=task,
                        goal_text=goal_text,
                        rendered_task_prompt=prompt,
                        worker_process=process,
                        initial_result=last_result,
                        parent_agent_config=self._agent_config,
                        runtime_factory=self._runtime_factory,
                        callbacks=self._callbacks,
                        phase_id=self._phase_id,
                        log_root=self._checkpoint_manager.root,
                        compact_if_needed=lambda r: self._compact_if_needed(process, r),
                    )
                except GoalValidationError as e:
                    self._goal_attempt_log.append(
                        {
                            "task": task.name,
                            "attempts": e.attempts,
                            "final_valid": False,
                        }
                    )
                    self._total_input_tokens += e.input_tokens
                    self._total_output_tokens += e.output_tokens
                    raise
                last_result = outcome.final_result
                self._total_input_tokens += outcome.total_input_tokens
                self._total_output_tokens += outcome.total_output_tokens
                self._goal_attempt_log.append(
                    {
                        "task": task.name,
                        "attempts": outcome.attempts,
                        "final_valid": True,
                    }
                )

    async def _run_memory_step(
        self,
        agent: BaseAgent[Any],
        context: dict[str, Any],
    ) -> tuple[str, int, int]:
        """Run the final summary turn. Returns (memory_text, input_tokens, output_tokens)."""
        user_additions = None
        if self._config.checkpoint is not None:
            user_additions = render_memory_prompt(self._config.checkpoint, self._config_dir, context)
        memory_prompt = self._checkpoint_manager.build_memory_prompt(user_additions)

        await self._callbacks.fire_before_agent_send(1)
        response = await agent.send(memory_prompt, allowed_tools=[])
        await self._callbacks.fire_agent_response(response, 1)
        return response.text, response.usage.input_tokens, response.usage.output_tokens

    async def execute(self, context: dict[str, Any]) -> PhaseOutcome:
        self.before_react()

        system_prompt = render_prompt(
            self._config_dir / "prompts" / f"{self._agent_name}.md",
            context,
            self._resolver,
        )
        runtime = self._runtime_factory.build_runtime(
            agent_config=self._agent_config,
            system_prompt=system_prompt,
            owner_id=self._phase_id,
        )
        process = ReActProcess(runtime, callbacks=self._callbacks)
        await self.run_tasks(process, context)

        self.after_react()

        memory_text, mem_in, mem_out = await self._run_memory_step(runtime.agent, context)

        extra: dict[str, Any] = {}
        if self._goal_attempt_log:
            extra["goal_validations"] = self._goal_attempt_log

        return PhaseOutcome(
            memory_text=memory_text,
            total_input_tokens=self._total_input_tokens + mem_in,
            total_output_tokens=self._total_output_tokens + mem_out,
            extra_checkpoint=extra,
        )

    async def on_error(self, error: MessageProcessingError | ProcessorHookError) -> None:
        payload: dict[str, Any] = {
            "status": "failed",
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "finished_at": datetime.now(UTC).isoformat(),
            "error": str(error.original_exception),
            "tokens": {
                "total_input": self._total_input_tokens,
                "total_output": self._total_output_tokens,
            },
        }
        if self._goal_attempt_log:
            payload["goal_validations"] = self._goal_attempt_log
        try:
            self._checkpoint_manager.write_phase_checkpoint(self._phase_id, payload)
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
