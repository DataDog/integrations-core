# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click #command line framework

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command("list", short_help='Show all versions of an integration') 
@click.argument('integration')
@click.pass_context
def list_versions(ctx: click.Context, integration: str):
    """Show all versions of an integration."""
    import httpx
    from packaging.version import Version

    url = "https://dd-integrations-core-wheels-build-stable.datadoghq.com/targets/simple/datadog-<INTEGRATION>/index.html"
    integration_url = url.replace("<INTEGRATION>", integration)

    response = httpx.request('GET', integration_url)
    versions = response.text.split('\n')[:-1]

    for i in range(len(versions)):
        version_number = versions[i].split('-')[1]
        versions[i] = Version(version_number)

    versions.sort()
    for ver in versions:
        print(str(ver))
