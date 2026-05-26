# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ddev.ai.agent.build import (
    make_agent_builder,
    make_goal_agent_builder,
    make_subagent_builder,
)
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.base import Phase, PhaseOutcome
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.goal import GOAL_TASK_SUFFIX, render_goal_text, run_goal_loop
from ddev.ai.phases.template import render_inline, render_prompt
from ddev.ai.react.process import ReActProcess
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import TOOL_MANIFEST

if TYPE_CHECKING:
    from ddev.ai.agent.base import BaseAgent
    from ddev.ai.agent.build import AgentBuilder, GoalAgentBuilder, SubagentBuilder
    from ddev.ai.phases.goal import GoalLoopOutcome
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
        agent_builder: AgentBuilder,
        checkpoint_manager: CheckpointManager,
        runtime_variables: dict[str, str],
        flow_variables: dict[str, str],
        config_dir: Path,
        file_registry: FileRegistry,
        subagent_builder: SubagentBuilder | None = None,
        goal_agent_builder: GoalAgentBuilder | None = None,
        callbacks: Callbacks | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__(
            phase_id=phase_id,
            dependencies=dependencies,
            config=config,
            checkpoint_manager=checkpoint_manager,
            runtime_variables=runtime_variables,
            flow_variables=flow_variables,
            config_dir=config_dir,
            file_registry=file_registry,
            callbacks=callbacks,
            logger=logger,
        )
        self._agent_builder = agent_builder
        self._subagent_builder = subagent_builder
        self._goal_agent_builder = goal_agent_builder
        self._goal_attempt_log: list[dict[str, Any]] = []
        self._subagent_log_dir = (
            checkpoint_manager.root / "subagents" / phase_id if subagent_builder is not None else None
        )

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
    def extra_init_kwargs(  # type: ignore[override]
        cls,
        *,
        phase_id: str,
        phase_config: PhaseConfig,
        agents: dict[str, AgentConfig],
        agent_clients: dict[str, Any],
        file_registry: FileRegistry,
        **_: Any,
    ) -> dict[str, Any]:
        if phase_config.agent is None:
            raise FlowConfigError(f"Phase {phase_id!r} (AgenticPhase) requires 'agent'")
        agent_config = agents[phase_config.agent]

        subagent_builder = None
        requires_subagent_builder = any(
            spec.requires_subagent_builder
            for name in agent_config.tools
            if (spec := TOOL_MANIFEST.get(name)) is not None
        )
        if requires_subagent_builder:
            subagent_builder = make_subagent_builder(
                parent_agent_config=agent_config,
                agent_clients=agent_clients,
                file_registry=file_registry,
            )

        any_goal = any((t.goal is not None or t.goal_path is not None) for t in phase_config.tasks)
        goal_agent_builder = None
        if any_goal:
            goal_agent_builder = make_goal_agent_builder(
                parent_agent_config=agent_config,
                agent_clients=agent_clients,
                file_registry=file_registry,
            )

        return {
            "agent_builder": make_agent_builder(
                agent_config=agent_config,
                agent_clients=agent_clients,
                file_registry=file_registry,
            ),
            "subagent_builder": subagent_builder,
            "goal_agent_builder": goal_agent_builder,
        }

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
    ) -> tuple[int, int]:
        """Run the task loop. Returns (total_input_tokens, total_output_tokens).

        Override to customize task execution — e.g. add retries, change ordering, etc.
        Default implementation iterates through config.tasks sequentially.
        """
        total_input = total_output = 0
        last_result: ReActResult | None = None
        goal_attempt_log: list[dict[str, Any]] = []

        for task in self._config.tasks:
            cin, cout = await self._compact_if_needed(process, last_result)
            total_input += cin
            total_output += cout

            has_goal = task.goal is not None or task.goal_path is not None
            prompt = render_task_prompt(task, self._config_dir, context, self._resolver)
            if has_goal:
                prompt = prompt + GOAL_TASK_SUFFIX

            last_result = await process.start(prompt)
            total_input += last_result.total_input_tokens
            total_output += last_result.total_output_tokens

            if has_goal:
                assert self._goal_agent_builder is not None
                goal_text = render_goal_text(task, self._config_dir, context, self._resolver)
                outcome: GoalLoopOutcome = await run_goal_loop(
                    task=task,
                    goal_text=goal_text,
                    rendered_task_prompt=prompt,
                    worker_process=process,
                    initial_result=last_result,
                    goal_agent_builder=self._goal_agent_builder,
                    callbacks=self._callbacks,
                    phase_id=self._phase_id,
                    log_root=self._checkpoint_manager.root,
                    compact_if_needed=lambda r: self._compact_if_needed(process, r),
                )
                last_result = outcome.final_result
                total_input += outcome.total_input_tokens
                total_output += outcome.total_output_tokens
                goal_attempt_log.append(
                    {
                        "task": task.name,
                        "attempts": outcome.attempts,
                        "final_valid": True,
                    }
                )

        self._goal_attempt_log = goal_attempt_log
        return total_input, total_output

    def _build_agent_and_process(self, context: dict[str, Any]) -> tuple[BaseAgent[Any], ReActProcess]:
        """Build the agent and ReAct process used to drive task execution."""
        system_prompt = render_prompt(
            self._config_dir / "prompts" / f"{self._config.agent}.md",
            context,
            self._resolver,
        )
        agent, tool_registry = self._agent_builder(
            system_prompt,
            self._phase_id,
            self._subagent_builder,
            self._subagent_log_dir,
        )
        process = ReActProcess(
            agent=agent,
            tool_registry=tool_registry,
            callbacks=self._callbacks,
        )
        return agent, process

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
        agent, process = self._build_agent_and_process(context)
        total_input, total_output = await self.run_tasks(process, context)
        self.after_react()

        memory_text, mem_in, mem_out = await self._run_memory_step(agent, context)

        extra: dict[str, Any] = {}
        if self._goal_attempt_log:
            extra["goal_validations"] = self._goal_attempt_log

        return PhaseOutcome(
            memory_text=memory_text,
            total_input_tokens=total_input + mem_in,
            total_output_tokens=total_output + mem_out,
            extra_checkpoint=extra,
        )
