# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.ai.config.dependency_graph import topological_sort
from ddev.ai.config.models import ResolvedFlow

if TYPE_CHECKING:
    from ddev.ai.config.models import FlowConfig, PhaseConfig, TaskConfig
    from ddev.ai.config.registry import ResourceRegistry


def build_resolved_flow(
    registry: ResourceRegistry,
    flow_name: str,
    fc: FlowConfig,
    scheduled_phases: list[PhaseConfig],
    resolved_variables: dict[str, str],
) -> ResolvedFlow:
    """Fold refs into their fields, resolve agents, and topo-sort into a ResolvedFlow."""
    return ResolvedFlow(
        name=flow_name,
        agents={pc.agent: registry.agents[pc.agent] for pc in scheduled_phases if pc.agent is not None},
        phases={pc.name: _inline_phase(registry, pc) for pc in scheduled_phases},
        flow=topological_sort(fc.flow),
        variables=resolved_variables,
    )


# TODO: create new dataclasses for inlined objects.
def _inline_phase(registry: ResourceRegistry, phase: PhaseConfig) -> PhaseConfig:
    tasks = [_inline_task(registry, task) for task in phase.tasks]
    checkpoint = phase.checkpoint
    if checkpoint is not None and checkpoint.memory_prompt_ref is not None:
        checkpoint = checkpoint.model_copy(
            update={
                "memory_prompt": registry.memories[checkpoint.memory_prompt_ref],
                "memory_prompt_ref": None,
            }
        )
    return phase.model_copy(update={"tasks": tasks, "checkpoint": checkpoint})


def _inline_task(registry: ResourceRegistry, task: TaskConfig) -> TaskConfig:
    update: dict[str, str | None] = {}
    if task.prompt_ref is not None:
        update["prompt"] = registry.prompts[task.prompt_ref]
        update["prompt_ref"] = None
    if task.goal_ref is not None:
        update["goal"] = registry.goals[task.goal_ref]
        update["goal_ref"] = None
    return task.model_copy(update=update) if update else task
