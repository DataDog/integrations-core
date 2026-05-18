# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Docker Registry v2 read-only helpers.

These helpers cover anonymous reads against any Docker Registry v2 endpoint
(`registry.datadoghq.com` is the default and serves the Datadog Agent image).
They are intentionally narrow: manifest existence checks and tag listings with
`Link: rel="next"` pagination per RFC 5988.
"""

from __future__ import annotations

import httpx

DEFAULT_REGISTRY_HOST = 'registry.datadoghq.com'

# Multi-arch (manifest list) is the canonical media type; OCI index and the
# single-arch fallbacks are accepted because the registry may serve any of
# these depending on which origin (GAR vs S3) responds.
MANIFEST_ACCEPT = ', '.join(
    [
        'application/vnd.docker.distribution.manifest.list.v2+json',
        'application/vnd.oci.image.index.v1+json',
        'application/vnd.docker.distribution.manifest.v2+json',
        'application/vnd.oci.image.manifest.v1+json',
    ]
)

# Large default page size keeps the common case to one round trip. Pagination
# is followed regardless, so the value is a performance hint, not a cap.
DEFAULT_PAGE_SIZE = 10000


def manifest_exists(
    repository: str,
    tag: str,
    *,
    host: str = DEFAULT_REGISTRY_HOST,
    timeout: float = 10.0,
) -> bool:
    """Return True if `<host>/v2/<repository>/manifests/<tag>` resolves, False on 404."""
    response = httpx.head(
        f'https://{host}/v2/{repository}/manifests/{tag}',
        headers={'Accept': MANIFEST_ACCEPT},
        follow_redirects=True,
        timeout=timeout,
    )
    if response.status_code == 404:
        return False
    response.raise_for_status()
    return True


def list_tags(
    repository: str,
    *,
    host: str = DEFAULT_REGISTRY_HOST,
    page_size: int = DEFAULT_PAGE_SIZE,
    timeout: float = 10.0,
) -> list[str]:
    """Return every tag published for `repository`, following `Link: rel="next"` pagination.

    Pagination is parsed via `httpx.Response.links`, which handles RFC 5988 quoting and
    multi-link headers correctly. Relative URLs in the next link are resolved against
    `host` (registries commonly return paths like `/v2/...?last=...`).
    """
    url: str | None = f'https://{host}/v2/{repository}/tags/list?n={page_size}'
    tags: list[str] = []
    while url is not None:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        page = response.json().get('tags') or []
        tags.extend(page)
        next_url = response.links.get('next', {}).get('url')
        if next_url and next_url.startswith('/'):
            next_url = f'https://{host}{next_url}'
        url = next_url
    return tags
