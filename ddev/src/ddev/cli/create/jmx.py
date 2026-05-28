# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from ddev.cli.create._common import create_options, dispatch

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('jmx', short_help='Scaffold a JMX integration')
@create_options
@click.pass_obj
def jmx(app: Application, **options: Any) -> None:
    """Scaffold a JMX-based integration."""
    dispatch(app, integration_type='jmx', **options)
