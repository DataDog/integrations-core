# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Resolve and validate the Agent image refs that `ddev release test-agent` dispatches against."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import httpx

from ddev.cli.release.test_agent import registry
from ddev.cli.release.test_agent.validation import Branch, ReleaseTarget

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ddev.cli.application import Application


@contextlib.contextmanager
def registry_errors(app: Application, scope: str) -> Iterator[None]:
    """Translate any `httpx.HTTPError` raised inside the block into a clean `app.abort` message.

    `scope` is interpolated into the abort text — e.g. `'tags'` for the tag listing or an
    image ref like `'registry.datadoghq.com/agent:7.80.0-rc.3'` for a manifest probe.
    """
    try:
        yield
    except httpx.HTTPError as e:
        app.abort(f'Failed to query registry.datadoghq.com for {scope}: {e}')


def resolve_version(app: Application, target: ReleaseTarget) -> str:
    """Pick the Agent image tag to test: the explicit tag, or the highest published RC for a branch."""
    if not isinstance(target, Branch):
        return target.name

    major_str, minor_str, _ = target.name.split('.')
    major, minor = int(major_str), int(minor_str)

    app.display_waiting(f'Looking up latest {major}.{minor}.0-rc.* in registry.datadoghq.com...')
    with registry_errors(app, 'tags'):
        tags = registry.list_agent_rc_tags(major, minor)
    if not tags:
        app.abort(
            f'No `{major}.{minor}.0-rc.*` tags found in registry.datadoghq.com/agent. '
            'Pass --tag explicitly once the first RC is published.'
        )
    latest = tags[-1]
    app.display_success(f'Latest RC: {latest}')
    return latest


def build_image_refs(version: str) -> tuple[str, str]:
    """Return the (linux, windows) image refs for the given Agent version."""
    base = f'registry.datadoghq.com/agent:{version}'
    return base, f'{base}-servercore'


def validate_images_exist(app: Application, version: str) -> None:
    """Check that both the Linux (`<version>`) and Windows (`<version>-servercore`) manifests are published."""
    for tag in (version, f'{version}-servercore'):
        image = f'registry.datadoghq.com/agent:{tag}'
        app.display_waiting(f'Checking `{image}`...')
        with registry_errors(app, f'`{image}`'):
            exists = registry.manifest_exists(tag)
        if not exists:
            app.abort(
                f'Image `{image}` not found in registry.datadoghq.com. Confirm the Agent release has been published.'
            )
