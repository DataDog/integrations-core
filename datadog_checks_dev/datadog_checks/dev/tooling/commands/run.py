# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from .utils import UNKNOWN_OPTIONS
from ..constants import get_root
from ...subprocess import run_command
from ...utils import chdir


@click.command(
    context_settings=UNKNOWN_OPTIONS,
    short_help='Run commands in the proper repo'
)
@click.argument('args', nargs=-1)
@click.pass_context
def run(ctx, args):
    """Run commands in the proper repo."""
    if not args:
        click.echo(ctx.get_help())
        return

    with chdir(get_root()):
        result = run_command(args)

    ctx.exit(result.code)
