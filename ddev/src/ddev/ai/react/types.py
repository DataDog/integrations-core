# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass

from ddev.ai.accounting.tokens import Tokens
from ddev.ai.agent.types import AgentResponse, ContextUsage


@dataclass(frozen=True)
class ReActResult:
    """Immutable summary of a completed ReAct loop run."""

    final_response: AgentResponse
    iterations: int
    tokens: Tokens  # sum across all iterations
    context_usage: ContextUsage | None  # promoted from final_response.usage.context_usage
