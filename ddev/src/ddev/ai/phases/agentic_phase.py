# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.build import AgentBuilder
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.base import Phase, PhaseOutcome
from ddev.ai.phases.checkpoint import CheckpointManager
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.template import render_inline, render_prompt
from ddev.ai.react.process import ReActProcess
from ddev.ai.tools.fs.file_registry import FileRegistry


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

        Override to customize task execution — e.g. add retries, change ordering, etc.
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

    def _build_agent_and_process(self, context: dict[str, Any]) -> tuple[BaseAgent[Any], ReActProcess]:
        """Build the agent and ReAct process used to drive task execution."""
        system_prompt = render_prompt(
            self._config_dir / "prompts" / f"{self._config.agent}.md",
            context,
            self._resolver,
        )
        agent, tool_registry = self._agent_builder(system_prompt, self._phase_id)
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
        if self._config.agent is None:
            raise FlowConfigError(f"Phase '{self._phase_id}': agent must be set before execute()")

        self.before_react()
        agent, process = self._build_agent_and_process(context)
        total_input, total_output = await self.run_tasks(process, context)
        self.after_react()

        memory_text, mem_in, mem_out = await self._run_memory_step(agent, context)

        return PhaseOutcome(
            memory_text=memory_text,
            total_input_tokens=total_input + mem_in,
            total_output_tokens=total_output + mem_out,
        )
