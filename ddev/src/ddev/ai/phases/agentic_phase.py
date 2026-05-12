# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.phases.base import Phase, PhaseOutcome
from ddev.ai.phases.config import AgentConfig, CheckpointConfig, FlowConfigError, PhaseConfig, TaskConfig
from ddev.ai.phases.template import render_inline, render_prompt
from ddev.ai.react.process import ReActProcess
from ddev.ai.tools.registry import ToolRegistry


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

    async def execute(self, context: dict[str, Any]) -> PhaseOutcome:
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
