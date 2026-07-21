# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Custom Textual Message subclasses mirroring the orchestrator callback events.

No widget imports — this module is safe to import anywhere in the TUI package.
"""

from __future__ import annotations

from textual.message import Message

from ddev.ai.agent.scope import AgentScope
from ddev.ai.agent.types import AgentResponse, ToolCall
from ddev.ai.react.types import ReActResult
from ddev.ai.tools.core.types import ToolResult


class PhaseStarted(Message):
    """Fired when a phase begins executing."""

    def __init__(self, phase_id: str) -> None:
        super().__init__()
        self.phase_id = phase_id


class PhaseFinished(Message):
    """Fired when a phase completes successfully."""

    def __init__(self, phase_id: str) -> None:
        super().__init__()
        self.phase_id = phase_id


class PhaseErrored(Message):
    """Fired when a phase terminates with an exception."""

    def __init__(self, phase_id: str, error: BaseException) -> None:
        super().__init__()
        self.phase_id = phase_id
        self.error = error


class RunErrored(Message):
    """Fired when orchestration stops because a phase failed."""


class ExecutionFailed(Message):
    """Fired when execution exits through an unexpected exception."""

    def __init__(self, error: BaseException) -> None:
        super().__init__()
        self.error = error


class AgentStarted(Message):
    """Fired once when an agent run begins, before the first send."""

    def __init__(self, scope: AgentScope, system_prompt: str, tools: list[str]) -> None:
        super().__init__()
        self.scope = scope
        self.system_prompt = system_prompt
        self.tools = tools


class AgentResponseReceived(Message):
    """Fired after every agent.send() returns."""

    def __init__(self, scope: AgentScope, response: AgentResponse, iteration: int) -> None:
        super().__init__()
        self.scope = scope
        self.response = response
        self.iteration = iteration


class AgentToolCalled(Message):
    """Fired once per (tool_call, result) pair after tools execute."""

    def __init__(self, scope: AgentScope, tool_call: ToolCall, result: ToolResult, iteration: int) -> None:
        super().__init__()
        self.scope = scope
        self.tool_call = tool_call
        self.result = result
        self.iteration = iteration


class AgentFinished(Message):
    """Fired when the ReAct loop exits cleanly."""

    def __init__(self, scope: AgentScope, result: ReActResult) -> None:
        super().__init__()
        self.scope = scope
        self.result = result


class AgentErrored(Message):
    """Fired when the ReAct loop aborts with an exception."""

    def __init__(self, scope: AgentScope, error: BaseException) -> None:
        super().__init__()
        self.scope = scope
        self.error = error


class BeforeCompact(Message):
    """Fired immediately before the agent's history is compacted."""

    def __init__(self, scope: AgentScope) -> None:
        super().__init__()
        self.scope = scope


class AfterCompact(Message):
    """Fired immediately after the agent's history has been compacted."""

    def __init__(self, scope: AgentScope) -> None:
        super().__init__()
        self.scope = scope


class ContextCleared(Message):
    """Fired immediately after the agent's conversation history is cleared."""

    def __init__(self, scope: AgentScope) -> None:
        super().__init__()
        self.scope = scope


class AgentBeforeSend(Message):
    """Fired just before each agent.send() with the prompt content (sentinel excluded)."""

    def __init__(self, scope: AgentScope, prompt: str, iteration: int) -> None:
        super().__init__()
        self.scope = scope
        self.prompt = prompt
        self.iteration = iteration


class BeforeGoalCheck(Message):
    """Fired immediately before each reviewer agent run for a task with a goal."""

    def __init__(self, phase_id: str, task_name: str, attempt: int) -> None:
        super().__init__()
        self.phase_id = phase_id
        self.task_name = task_name
        self.attempt = attempt


class AfterGoalCheck(Message):
    """Fired after each reviewer agent run, with the parsed verdict."""

    def __init__(
        self,
        phase_id: str,
        task_name: str,
        attempt: int,
        valid: bool,
        reason: str,
    ) -> None:
        super().__init__()
        self.phase_id = phase_id
        self.task_name = task_name
        self.attempt = attempt
        self.valid = valid
        self.reason = reason
