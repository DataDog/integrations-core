# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class FlowConfigError(Exception):
    """Wraps Pydantic ValidationError or YAML errors with a user-friendly message."""


def detect_cycles(
    dependency_map: dict[str, list[str]],
    limit: int = 50,
) -> tuple[list[list[str]], bool]:
    """Return every simple cycle in the dependency graph, each as an ordered list of phase IDs."""
    rank = {n: i for i, n in enumerate(dependency_map)}
    cycles: list[list[str]] = []

    def dfs(start: str, current: str, path: list[str], on_path: set[str]) -> bool:
        for dep in dependency_map.get(current, []):
            if dep == start:
                cycles.append(path + [start])
                if len(cycles) >= limit:
                    return True
            elif dep in rank and rank[dep] > rank[start] and dep not in on_path:
                on_path.add(dep)
                if dfs(start, dep, path + [dep], on_path):
                    return True
                on_path.discard(dep)
        return False

    for start in dependency_map:
        if dfs(start, start, [start], {start}):
            return cycles, True
    return cycles, False
