# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import click


@click.command(context_settings={'ignore_unknown_options': True}, hidden=True)
@click.argument('intg_name')
@click.argument('environment')
@click.argument('args', nargs=-1)
@click.option('--config')
@click.pass_context
def check(ctx: click.Context, *, intg_name: str, environment: str, args: tuple[str, ...], config: str | None):
    from ddev.cli.env.agent import agent

    ctx.invoke(agent, intg_name=intg_name, environment=environment, args=('check', *args), config_file=config)
