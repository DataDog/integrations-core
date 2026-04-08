# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod
from copy import deepcopy

from ddev.ai.agent.types import AgentResponse, ToolResultMessage


class BaseAgent[TMessage](ABC):
    """Abstract base class for all agent implementations.

    Provides shared, provider-agnostic history management. The message type
    TMessage is supplied by each concrete provider (e.g. MessageParam for Anthropic).
    Subclasses must implement send().
    """

    def __init__(self) -> None:
        self._history: list[TMessage] = []

    @property
    def history(self) -> list[TMessage]:
        """Read-only snapshot of the conversation history."""
        return deepcopy(self._history)

    def reset(self) -> None:
        """Clear conversation history to start a new conversation."""
        self._history = []

    @abstractmethod
    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse: ...
