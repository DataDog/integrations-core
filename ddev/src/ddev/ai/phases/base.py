# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any, Protocol

from ddev.ai.agent.types import AgentProtocol
from ddev.ai.phases.checkpoint import CheckpointManager, validate_checkpoint_output
from ddev.ai.phases.config import PhaseConfig
from ddev.ai.phases.messages import (
    PhaseCompleteMessage,
    PhaseFailedMessage,
    PipelineStartMessage,
    make_phase_complete_type,
)
from ddev.ai.phases.template import render_prompt
from ddev.ai.react.process import ReActCallback, ReActProcess, ReActResult
from ddev.ai.tools.core.registry import ToolRegistry
from ddev.event_bus.orchestrator import AsyncProcessor


class AgentFactory(Protocol):
    """Creates a fresh AgentProtocol instance for each phase execution.

    Called once per process_message invocation with the phase-specific name,
    rendered system prompt, and tool registry. The implementation is responsible
    for any provider-specific configuration (model, max_tokens, API client, etc.).
    """

    def __call__(self, name: str, system_prompt: str, tool_registry: ToolRegistry) -> AgentProtocol: ...


class Phase(AsyncProcessor[PipelineStartMessage | PhaseCompleteMessage]):
    """Generic AsyncProcessor that drives one agent through a multi-prompt ReAct loop.

    Subclass this only if you need custom logic beyond what config supports.
    For most phases, instantiate Phase directly with a PhaseConfig.

    The config must be pre-loaded via PhaseConfig.from_yaml() before instantiation.
    """

    def __init__(
        self,
        config: PhaseConfig,
        agent_factory: AgentFactory,
        callbacks: list[ReActCallback] | None = None,
    ) -> None:
        super().__init__(name=config.name)
        self._config = config
        self._agent_factory = agent_factory
        self._callbacks: list[ReActCallback] = callbacks or []
        self._checkpoint_path: Path | None = None
        self._metadata: dict[str, Any] = {}

    async def process_message(self, message: PipelineStartMessage | PhaseCompleteMessage) -> None:
        self._checkpoint_path = Path(message.checkpoint_path)
        self._metadata = message.metadata

        # CheckpointManager and ToolRegistry are created fresh per call:
        # checkpoint_path is only known at message time, and tools must not share
        # state across different pipeline runs.
        checkpoint_mgr = CheckpointManager(self._checkpoint_path)
        tool_registry = ToolRegistry.from_names(self._config.tools)

        # checkpoint_data is read once here and never refreshed during this phase's execution.
        # The file does not change while a phase runs — writes happen only at phase completion.
        # In parallel execution, this snapshot-at-start ensures each phase sees only the output
        # of phases that completed before it, which is the correct and intentional behaviour.
        template_context: dict[str, Any] = {
            "checkpoint_data": checkpoint_mgr.as_yaml_string(),
            "phase_name": self._config.name,
            "metadata": self._metadata,
        }

        system_prompt = render_prompt(self._config.system_prompt_path, template_context)
        agent = self._agent_factory(self._config.name, system_prompt, tool_registry)
        react = ReActProcess(
            agent=agent,
            tool_registry=tool_registry,
            max_iterations=self._config.react.max_iterations,
            callbacks=self._callbacks,
        )

        last_result: ReActResult | None = None

        for task_prompt_path in self._config.task_prompt_paths:
            # Reset agent history if context usage exceeds the configured threshold.
            # checkpoint_data remains available in the template context for recovery.
            if last_result is not None and last_result.context_usage is not None:
                if last_result.context_usage.context_pct >= self._config.agent.context_reset_threshold_pct:
                    agent.reset()

            prompt = render_prompt(task_prompt_path, template_context)
            last_result = await react.start(prompt)

        # task_prompt_paths is guaranteed non-empty by PhaseConfig.from_yaml validation
        assert last_result is not None

        # raises CheckpointValidationError if response is not valid YAML or missing required keys
        output = validate_checkpoint_output(last_result.final_response.text, self._config.checkpoint_schema)
        output["status"] = "success"
        checkpoint_mgr.write_phase(self._config.name, output)

    async def on_success(self, message: PipelineStartMessage | PhaseCompleteMessage) -> None:
        assert self._checkpoint_path is not None
        complete_type = make_phase_complete_type(self._config.name)
        self.submit_message(
            complete_type(
                id=f"{self._config.name}_complete_{message.id}",
                phase_name=self._config.name,
                checkpoint_path=str(self._checkpoint_path),
                metadata=self._metadata,
            )
        )

    async def on_error(self, message: PipelineStartMessage | PhaseCompleteMessage, error: Exception) -> None:
        if self._checkpoint_path is not None:
            CheckpointManager(self._checkpoint_path).write_phase(
                self._config.name,
                {"status": "failed", "error": str(error)},
            )
        self.submit_message(
            PhaseFailedMessage(
                id=f"{self._config.name}_failed_{message.id}",
                phase_name=self._config.name,
                checkpoint_path=str(self._checkpoint_path or ""),
                error=str(error),
            )
        )
