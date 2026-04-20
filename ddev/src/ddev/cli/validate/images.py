# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Validate Docker image inventory')
@click.option('--sync', is_flag=True, help='Rewrite .ddev/docker-images.json')
@click.pass_obj
def images(app: Application, sync: bool) -> None:
    """Validate Docker image inventory."""
    app.display_info('images validator not yet implemented')
