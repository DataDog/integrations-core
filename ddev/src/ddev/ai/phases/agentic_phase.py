# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from ddev.ai.agent.scope import AgentRole, AgentScope
from ddev.ai.config.errors import ConfigError
from ddev.ai.config.models import AgentConfig, PhaseConfig, TaskConfig
from ddev.ai.phases.base import FlowContext, Phase, PhaseOutcome
from ddev.ai.phases.goal import GOAL_TASK_SUFFIX, GoalValidationError, run_goal_loop
from ddev.ai.phases.template import render_inline
from ddev.ai.react.process import ReActProcess
from ddev.ai.runtime.checkpoints import (
    CheckpointManager,
    CheckpointStatus,
    CheckpointTokenInfo,
    FailedCheckpoint,
    GoalValidationRecord,
)

if TYPE_CHECKING:
    from ddev.ai.phases.goal import GoalLoopOutcome
    from ddev.ai.phases.resources import PhaseResources
    from ddev.ai.react.factory import ReActProcessFactory
    from ddev.ai.react.types import ReActResult


RESUME_NOTICE = """

---

NOTE FROM THE HARNESS — RESUMED RUN

This phase is being re-run because a previous execution of this flow failed or was
interrupted while this phase was the one in progress. You are picking up from where it stopped.

Some of this phase's work may already be partially on disk from that earlier attempt — files
created or half-edited, assets generated, commands partially applied. Before doing new work,
inspect the current state of the files this phase is responsible for, reconcile anything that is
incomplete or inconsistent, and avoid blindly duplicating steps that were already finished.
Treat the on-disk state as the source of truth and bring it to a correct, complete result."""

RESUME_NOTICE_ERROR = """

The previous attempt recorded this error:

{error}"""


def build_resume_notice(error: str | None) -> str:
    notice = RESUME_NOTICE
    if error:
        notice += RESUME_NOTICE_ERROR.format(error=error)
    return notice


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
        process_factory: ReActProcessFactory,
    ) -> None:
        super().__init__(
            phase_id=phase_id,
            dependencies=dependencies,
            config=config,
            checkpoint_manager=checkpoint_manager,
            context=context,
        )
        self._agent_config = agent_config
        self._process_factory = process_factory
        self._scope = AgentScope(owner_id=phase_id, role=AgentRole.PHASE, phase_id=phase_id)
        self._goal_attempt_log: list[GoalValidationRecord] = []
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0

    @classmethod
    def validate_config(cls, phase_id: str, config: PhaseConfig) -> None:
        if config.agent is None:
            raise ConfigError(f"Phase {phase_id!r} (AgenticPhase) requires 'agent'")
        if not config.tasks:
            raise ConfigError(f"Phase {phase_id!r} (AgenticPhase) must have at least one task")

    @classmethod
    def build(
        cls,
        phase_id: str,
        config: PhaseConfig,
        deps: list[str],
        resources: PhaseResources,
        checkpoint_manager: CheckpointManager,
        context: FlowContext,
    ) -> AgenticPhase:
        # config.agent is guaranteed non-None by validate_config; the engine's
        # _validate_phase_agent guarantees it names a registered, non-broken agent
        # before this flow can ever reach a resolved, runnable state.
        agent_name = cast(str, config.agent)
        agent_config = resources.agent_config(agent_name)
        process_factory = resources.process_factory

        return cls(
            phase_id=phase_id,
            dependencies=deps,
            config=config,
            checkpoint_manager=checkpoint_manager,
            context=context,
            agent_config=agent_config,
            process_factory=process_factory,
        )

    def before_react(self) -> None:
        """Called once before agent/tools are created. Override for phase-specific setup."""

    def after_react(self) -> None:
        """Called once after all tasks complete. Override for phase-specific teardown."""

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
            last_result = await self.run_task(process, task, context, last_result)

    async def run_task(
        self,
        process: ReActProcess,
        task: TaskConfig,
        context: dict[str, Any],
        last_result: ReActResult | None,
    ) -> ReActResult:
        """Run one task and return the result to use for the next task."""
        await self._manage_context(process, task, last_result)

        has_goal = self._task_has_goal(task)
        prompt = self._render_task_prompt(task, context, has_goal)
        result = await self._start_task(process, prompt)

        if not has_goal:
            return result

        return await self._run_goal_validation(process, task, context, prompt, result)

    async def _manage_context(
        self,
        process: ReActProcess,
        task: TaskConfig,
        last_result: ReActResult | None,
    ) -> None:
        if task.clear_context_before:
            await process.reset()
            return

        if task.compact_context_before:
            input_tokens, output_tokens = await process.compact()
            self._add_tokens(input_tokens, output_tokens)
            return

        input_tokens, output_tokens = await self._compact_if_needed(process, last_result)
        self._add_tokens(input_tokens, output_tokens)

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

    def _task_has_goal(self, task: TaskConfig) -> bool:
        return task.goal is not None

    def _render_task_prompt(
        self,
        task: TaskConfig,
        context: dict[str, Any],
        has_goal: bool,
    ) -> str:
        prompt = render_inline(cast(str, task.prompt), context, self._resolver)
        if has_goal:
            return prompt + GOAL_TASK_SUFFIX
        return prompt

    async def _start_task(
        self,
        process: ReActProcess,
        prompt: str,
    ) -> ReActResult:
        result = await process.start(prompt)
        self._add_tokens(result.total_input_tokens, result.total_output_tokens)
        return result

    async def _run_goal_validation(
        self,
        process: ReActProcess,
        task: TaskConfig,
        context: dict[str, Any],
        prompt: str,
        result: ReActResult,
    ) -> ReActResult:
        goal_text = render_inline(cast(str, task.goal), context, self._resolver)
        try:
            outcome: GoalLoopOutcome = await run_goal_loop(
                task=task,
                goal_text=goal_text,
                rendered_task_prompt=prompt,
                worker_process=process,
                initial_result=result,
                parent_agent_config=self._agent_config,
                process_factory=self._process_factory,
                callbacks=self._callbacks,
                phase_id=self._phase_id,
                compact_if_needed=lambda r: self._compact_if_needed(process, r),
            )
        except GoalValidationError as e:
            self._record_goal_attempt(task, e.attempts, final_valid=False)
            self._add_tokens(e.input_tokens, e.output_tokens)
            raise

        self._record_goal_attempt(task, outcome.attempts, final_valid=True)
        self._add_tokens(outcome.total_input_tokens, outcome.total_output_tokens)
        return outcome.final_result

    def _record_goal_attempt(
        self,
        task: TaskConfig,
        attempts: int,
        *,
        final_valid: bool,
    ) -> None:
        self._goal_attempt_log.append(
            GoalValidationRecord(
                task=task.name,
                attempts=attempts,
                final_valid=final_valid,
            )
        )

    def _add_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

    async def _run_memory_step(
        self,
        process: ReActProcess,
        context: dict[str, Any],
    ) -> tuple[str, int, int]:
        """Run the final summary turn. Returns (memory_text, input_tokens, output_tokens)."""
        user_additions = None
        if self._config.checkpoint is not None:
            user_additions = render_inline(cast(str, self._config.checkpoint.memory_prompt), context)
        memory_prompt = self._checkpoint_manager.build_memory_prompt(user_additions)

        response = await process.run_once(memory_prompt)
        return response.text, response.usage.input_tokens, response.usage.output_tokens

    async def execute(self, context: dict[str, Any]) -> PhaseOutcome:
        self.before_react()

        system_prompt = render_inline(self._agent_config.system_prompt, context, self._resolver)
        if self._is_resume_frontier:
            prior = (context.get("checkpoints") or {}).get(self._phase_id)
            error = prior.error if prior is not None and prior.status == CheckpointStatus.FAILED else None
            system_prompt += build_resume_notice(error)
        try:
            process = self._process_factory.create(
                scope=self._scope,
                agent_config=self._agent_config,
                system_prompt=system_prompt,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create process for phase {self._phase_id}: {e}") from e

        await self.run_tasks(process, context)

        self.after_react()

        memory_text, mem_in, mem_out = await self._run_memory_step(process, context)

        return PhaseOutcome(
            memory_text=memory_text,
            total_input_tokens=self._total_input_tokens + mem_in,
            total_output_tokens=self._total_output_tokens + mem_out,
            goal_validations=self._goal_attempt_log or None,
        )

    def build_failed_checkpoint(self, error: BaseException) -> FailedCheckpoint:
        """Include partial token and goal progress in a failed checkpoint."""
        checkpoint = super().build_failed_checkpoint(error)
        checkpoint.tokens = CheckpointTokenInfo(
            total_input=self._total_input_tokens,
            total_output=self._total_output_tokens,
        )
        checkpoint.goal_validations = self._goal_attempt_log or None
        return checkpoint
