# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess

import click

from .... import chdir
from ...constants import get_root
from ..console import CONTEXT_SETTINGS, abort
from .utils import insert_verbosity_flag


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Build documentation')
@click.option('--verbose', '-v', count=True, help='Increase verbosity (can be used additively)')
def build(verbose):
    """Build documentation."""
    command = ['tox', '-e', 'docs', 'build']
    insert_verbosity_flag(command, verbose)

    with chdir(get_root()):
        process = subprocess.run(command)

    abort(code=process.returncode)
