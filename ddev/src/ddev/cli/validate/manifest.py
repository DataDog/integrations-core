# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Validate integration manifests')
@click.argument('integrations', nargs=-1)
@click.pass_context
def manifest(ctx: click.Context, integrations: tuple[str, ...]):
    """Validate integration manifests."""
    import httpx

    app: Application = ctx.obj
    validation_tracker = app.create_validation_tracker('Manifests')

    dd_url = app.config.org.config.get('dd_url', '')
    if not dd_url:
        app.abort(f'No `dd_url` has been set for org `{app.config.org.name}`')

    validation_endpoint = f'{dd_url}/api/beta/apps/manifest/validate'

    for integration in app.repo.integrations.iter(integrations):
        payload = {'data': {'type': 'app_manifest', 'attributes': integration.manifest.get('')}}

        try:
            response = httpx.post(validation_endpoint, json=payload)

            if response.status_code == 400:
                for error in response.json()['errors']:
                    validation_tracker.error((integration.display_name, 'manifest.json'), message=error)
            else:
                response.raise_for_status()
                validation_tracker.success()
        except Exception as e:
            validation_tracker.error((integration.display_name, 'manifest.json'), message=str(e))

    if validation_tracker.errors:
        validation_tracker.display()
        app.abort()

    validation_tracker.display()
