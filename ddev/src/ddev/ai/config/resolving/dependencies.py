# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.ai.config.dependency_graph import detect_cycles
from ddev.ai.config.errors import ErrorKind, FlowError

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.ai.config.models import FlowConfig


def validate_dependencies(fc: FlowConfig, flow_name: str, flow_src: Path) -> list[FlowError]:
    """Check the flow's schedule for duplicates, unscheduled dependencies, and cycles."""
    dependency_map = {fe.phase: fe.dependencies for fe in fc.flow}
    return [
        *_check_duplicate_schedule(fc, flow_name, flow_src),
        *_check_unscheduled_dependencies(fc, flow_name, dependency_map, flow_src),
        *_check_dependency_cycles(flow_name, dependency_map, flow_src),
    ]


def _check_duplicate_schedule(fc: FlowConfig, flow_name: str, flow_src: Path) -> list[FlowError]:
    seen: set[str] = set()
    errors: list[FlowError] = []
    for fe in fc.flow:
        if fe.phase in seen:
            errors.append(
                FlowError(
                    ErrorKind.DEPENDENCY,
                    f"Phase {fe.phase!r} is scheduled more than once in flow {flow_name!r}",
                    subject=fe.phase,
                    phase=fe.phase,
                    sources=[flow_src],
                )
            )
        seen.add(fe.phase)
    return errors


def _check_unscheduled_dependencies(
    fc: FlowConfig, flow_name: str, dependency_map: dict[str, list[str]], flow_src: Path
) -> list[FlowError]:
    errors: list[FlowError] = []
    for fe in fc.flow:
        for dep in fe.dependencies:
            if dep not in dependency_map:
                errors.append(
                    FlowError(
                        ErrorKind.DEPENDENCY,
                        f"Phase {fe.phase!r} depends on {dep!r}, which is not scheduled in flow {flow_name!r}",
                        subject=dep,
                        phase=fe.phase,
                        sources=[flow_src],
                    )
                )
    return errors


def _check_dependency_cycles(flow_name: str, dependency_map: dict[str, list[str]], flow_src: Path) -> list[FlowError]:
    cycles, truncated = detect_cycles(dependency_map)
    errors = [
        FlowError(
            ErrorKind.DEPENDENCY,
            f"Dependency cycle detected in flow {flow_name!r}: {' -> '.join(cycle)}",
            sources=[flow_src],
        )
        for cycle in cycles
    ]
    if truncated:
        errors.append(
            FlowError(
                ErrorKind.DEPENDENCY,
                f"Cycle detection truncated in flow {flow_name!r} (too many cycles)",
                sources=[flow_src],
            )
        )
    return errors
