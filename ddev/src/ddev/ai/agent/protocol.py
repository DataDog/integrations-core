# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Protocol

from ddev.ai.agent.types import AgentResponse, ToolResultMessage


class AgentProtocol(Protocol):
    """Structural interface that any agent must satisfy to be used by ReActProcess."""

    async def send(
        self,
        content: str | list[ToolResultMessage],
        allowed_tools: list[str] | None = None,
    ) -> AgentResponse:
        """Send a prompt or tool results and return the agent's response."""
        ...

    def reset(self) -> None:
        """Clear conversation history to start a new conversation."""
        ...
