# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from ddev.cli.create._common import create_options, dispatch

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('check-only', short_help='Scaffold check-only files inside an existing integration directory')
@create_options
@click.pass_obj
def check_only(app: Application, **options: Any) -> None:
    """Add Python check scaffolding to an existing integration directory."""
    dispatch(app, integration_type='check_only', **options)
