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
@click.option('--pdf', is_flag=True, help='Also export the site as PDF')
def build(verbose, pdf):
    """Build documentation."""
    command = ['tox', '-e', 'docs', '--', 'build', '--clean']
    insert_verbosity_flag(command, verbose)

    env_vars = {'ENABLE_PDF_SITE_EXPORT': '1' if pdf else '0'}

    with chdir(get_root(), env_vars=env_vars):
        process = subprocess.run(command)

    abort(code=process.returncode)
