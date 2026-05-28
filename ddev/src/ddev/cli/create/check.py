# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from ddev.cli.create._common import create_options, dispatch

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('check', short_help='Scaffold a check-based integration')
@create_options
@click.pass_obj
def check(app: Application, **options: Any) -> None:
    """Scaffold a check-based integration."""
    dispatch(app, integration_type='check', **options)
