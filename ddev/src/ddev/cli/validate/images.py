# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.cli.validate.images_utils import (
    diff_manifests,
    load_manifest,
    scan_repo,
    write_manifest,
)

if TYPE_CHECKING:
    from ddev.cli.application import Application


MANIFEST_RELATIVE_PATH = '.ddev/docker-images.json'


@click.command(short_help='Validate Docker image inventory')
@click.argument('integrations', nargs=-1)
@click.option('--sync', is_flag=True, help='Rewrite .ddev/docker-images.json in place')
@click.pass_obj
def images(app: Application, integrations: tuple[str, ...], sync: bool) -> None:
    """Validate Docker image inventory.

    Without --sync, fails when .ddev/docker-images.json does not match a fresh
    scan of the repo. With --sync, rewrites the manifest.
    """
    tracker = app.create_validation_tracker('Docker images')

    config = app.repo.config.get('/docker-images') or {}
    mirror_prefixes: list[str] = list(config.get('mirror-prefixes') or [])
    exclude_globs: list[str] = list(config.get('exclude') or [])

    selection = integrations or ('all',)
    integration_names = [check.name for check in app.repo.integrations.iter(selection)]

    manifest_path = app.repo.path / MANIFEST_RELATIVE_PATH
    current = scan_repo(
        repo_path=app.repo.path,
        integrations=integration_names,
        mirror_prefixes=mirror_prefixes,
        exclude_globs=exclude_globs,
    )
    on_disk = load_manifest(manifest_path)
    diff = diff_manifests(on_disk, current)

    if diff.is_empty():
        tracker.success()
    elif sync:
        write_manifest(manifest_path, current)
        tracker.success()
    else:
        affected = sorted({*diff.added_images, *diff.removed_images, *diff.modified_images})
        tracker.error(
            ('docker-images', MANIFEST_RELATIVE_PATH),
            message=(
                f'Manifest drift detected for: {", ".join(affected)}\n'
                f'Added: {diff.added_images or "(none)"}\n'
                f'Removed: {diff.removed_images or "(none)"}\n'
                f'Modified: {diff.modified_images or "(none)"}\n'
                f'Run `ddev validate images --sync` to update.'
            ),
        )

    tracker.display()
    if tracker.errors:
        app.abort()
