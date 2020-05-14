# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
import webbrowser

import click

from ....utils import chdir
from ...constants import get_root
from ..console import CONTEXT_SETTINGS, abort
from .utils import insert_verbosity_flag


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Serve and view documentation in a web browser')
@click.option('--no-open', '-n', is_flag=True, help='Do not open the documentation in a web browser')
@click.option('--verbose', '-v', count=True, help='Increase verbosity (can be used additively)')
@click.option('--pdf', is_flag=True, help='Also export the site as PDF')
def serve(no_open, verbose, pdf):
    """Serve and view documentation in a web browser."""
    address = 'localhost:8000'

    command = ['tox', '-e', 'docs', '--', 'serve', '--livereload', '--dev-addr', address]
    insert_verbosity_flag(command, verbose)

    if pdf:
        os.environ["ENABLE_PDF_SITE_EXPORT"] = '1'

    if not no_open:
        webbrowser.open_new_tab(f'http://{address}')

    with chdir(get_root()):
        process = subprocess.run(command)

    abort(code=process.returncode)
