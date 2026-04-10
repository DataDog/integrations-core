# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass

from ddev.ai.agent.types import AgentResponse, ContextUsage


@dataclass(frozen=True)
class ReActResult:
    """Immutable summary of a completed ReAct loop run."""

    final_response: AgentResponse
    iterations: int
    total_input_tokens: int  # sum across all iterations
    total_output_tokens: int  # sum across all iterations
    context_usage: ContextUsage | None  # promoted from final_response.usage.context_usage
