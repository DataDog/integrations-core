# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Agent-specific wrappers around `ddev.utils.docker_registry`.

The Datadog Agent image is served by `registry.datadoghq.com/agent`. This
module fixes that repository name and exposes the only agent-specific
operation we need today: filtering the published tag list down to the
`MAJ.MIN.0-rc.N` RCs for a given release line.
"""

from __future__ import annotations

import re

from packaging.version import InvalidVersion, Version

from ddev.utils import docker_registry

AGENT_REPOSITORY = 'agent'


def manifest_exists(tag: str, *, timeout: float = 10.0) -> bool:
    """Return True if `registry.datadoghq.com/agent:<tag>` resolves to a manifest, False on 404."""
    return docker_registry.manifest_exists(AGENT_REPOSITORY, tag, timeout=timeout)


def list_agent_rc_tags(major: int, minor: int, *, timeout: float = 10.0) -> list[str]:
    """Return all `<major>.<minor>.0-rc.N` tags published to the Agent registry, sorted ascending by version."""
    pattern = re.compile(rf'^{major}\.{minor}\.0-rc\.\d+$')
    raw_tags = docker_registry.list_tags(AGENT_REPOSITORY, timeout=timeout)
    matches: list[tuple[Version, str]] = []
    for tag in raw_tags:
        if not pattern.match(tag):
            continue
        try:
            matches.append((Version(tag), tag))
        except InvalidVersion:
            continue
    return [tag for _, tag in sorted(matches, key=lambda pair: pair[0])]
