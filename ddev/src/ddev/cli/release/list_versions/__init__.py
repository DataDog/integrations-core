# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command("list", short_help='Show all versions of an integration')
@click.argument('integration')
@click.pass_context
def list_versions(ctx: click.Context, integration: str):
    """Show all versions of an integration."""
    import httpx
    from packaging.version import Version

    int_name = integration.replace('_', '-')
    ignored_prefix = 'datadog-'
    if int_name.startswith(ignored_prefix):
        int_name = int_name[len(ignored_prefix) :]

    url = f'https://dd-integrations-core-wheels-build-stable.datadoghq.com/targets/simple/datadog-{int_name}/index.html'

    response = httpx.get(url)
    versions = response.text.splitlines()

    version_numbers = []
    for line in versions:
        version_number = line.split('-')[1]
        version_numbers.append(Version(version_number))

    version_numbers.sort()

    app: Application = ctx.obj
    for ver in version_numbers:
        app.display(str(ver))
