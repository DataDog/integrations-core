# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Docker Registry v2 helpers for the public Datadog Agent registry.

`registry.datadoghq.com` exposes the standard Docker Registry v2 API and serves
the Agent image (`agent`) anonymously, so no authentication is needed for read
operations. See the Agent Delivery "Command Reference" runbook for the manual
equivalent commands.
"""

from __future__ import annotations

import re

import httpx
from packaging.version import InvalidVersion, Version

REGISTRY_HOST = 'registry.datadoghq.com'
AGENT_REPOSITORY = 'agent'

# Multi-arch (manifest list) is the canonical type for the Agent image; OCI
# index is accepted as a fallback because the registry may serve either depending
# on which origin (GAR vs S3) responds.
_MANIFEST_ACCEPT = ', '.join(
    [
        'application/vnd.docker.distribution.manifest.list.v2+json',
        'application/vnd.oci.image.index.v1+json',
        'application/vnd.docker.distribution.manifest.v2+json',
        'application/vnd.oci.image.manifest.v1+json',
    ]
)


def manifest_url(tag: str) -> str:
    return f'https://{REGISTRY_HOST}/v2/{AGENT_REPOSITORY}/manifests/{tag}'


def tags_list_url() -> str:
    return f'https://{REGISTRY_HOST}/v2/{AGENT_REPOSITORY}/tags/list'


def manifest_exists(tag: str, *, timeout: float = 10.0) -> bool:
    """Return True if `registry.datadoghq.com/agent:<tag>` resolves to a manifest, False on 404."""
    response = httpx.head(
        manifest_url(tag),
        headers={'Accept': _MANIFEST_ACCEPT},
        follow_redirects=True,
        timeout=timeout,
    )
    if response.status_code == 404:
        return False
    response.raise_for_status()
    return True


def list_agent_rc_tags(major: int, minor: int, *, timeout: float = 10.0) -> list[str]:
    """Return all `<major>.<minor>.0-rc.N` tags published to the Agent registry, sorted ascending by version."""
    response = httpx.get(tags_list_url(), timeout=timeout)
    response.raise_for_status()
    raw_tags = response.json().get('tags') or []
    pattern = re.compile(rf'^{major}\.{minor}\.0-rc\.\d+$')
    matches: list[tuple[Version, str]] = []
    for tag in raw_tags:
        if not pattern.match(tag):
            continue
        try:
            matches.append((Version(tag), tag))
        except InvalidVersion:
            continue
    return [tag for _, tag in sorted(matches, key=lambda pair: pair[0])]
