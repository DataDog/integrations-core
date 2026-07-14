# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from ddev.ai.config.models import FlowEntry


def detect_cycles(
    dependency_map: dict[str, list[str]],
    limit: int = 50,
) -> tuple[list[list[str]], bool]:
    """Return every simple cycle in the dependency graph, each as an ordered list of phase IDs."""
    # Enumerate every simple cycle exactly once: from each node, DFS only through
    # higher-ranked nodes, so each cycle is reported only when started from its
    # lowest-ranked member. (Tiernan-style enumeration with rank canonicalization.)
    rank = {n: i for i, n in enumerate(dependency_map)}
    cycles: list[list[str]] = []

    class _LimitReached(Exception):
        """Raised when the cycle limit is reached."""

        pass

    def dfs(start: str, current: str, path: list[str], on_path: set[str]):
        for dep in dependency_map.get(current, []):
            if dep == start:
                cycles.append(path + [start])
                if len(cycles) >= limit:
                    raise _LimitReached
            elif dep in rank and rank[dep] > rank[start] and dep not in on_path:
                on_path.add(dep)
                dfs(start, dep, path + [dep], on_path)
                on_path.discard(dep)

    try:
        for start in dependency_map:
            dfs(start, start, [start], {start})
    except _LimitReached:
        return cycles, True
    return cycles, False


def topological_sort(flow: list[FlowEntry]) -> list[FlowEntry]:
    """Stable topological sort of an acyclic flow: dependencies before dependents.

    Phases with no ordering constraint between them keep their original
    declaration order. The caller must guarantee the graph is acyclic.
    """
    remaining_deps = {entry.phase: set(entry.dependencies) for entry in flow}

    ordered: list[FlowEntry] = []
    emitted: set[str] = set()
    while len(ordered) < len(flow):
        nxt = next(entry for entry in flow if entry.phase not in emitted and remaining_deps[entry.phase] <= emitted)
        ordered.append(nxt)
        emitted.add(nxt.phase)
    return ordered
