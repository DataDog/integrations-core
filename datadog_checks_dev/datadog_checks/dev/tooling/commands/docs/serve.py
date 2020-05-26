# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
import webbrowser

import click

from ....utils import chdir
from ...constants import get_root
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_waiting, echo_warning
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

    env_vars = {'ENABLE_PDF_SITE_EXPORT': '1' if pdf else '0'}

    address = f'http://{address}'
    build_completion_indicator = f'Serving on {address}'
    build_complete = False

    # TODO: Investigate why messages are logged twice, then submit upstream fix (to tornado or livereload)
    info_prefixes = ('[I ', 'INFO ')
    warning_prefixes = ('[W ', 'WARNING ')
    error_prefixes = ('[E ', 'ERROR ')

    with chdir(get_root(), env_vars=env_vars):
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:

            # To avoid blocking never use a pipe's file descriptor iterator. See https://bugs.python.org/issue3907
            for line in iter(process.stdout.readline, b''):
                line = line.decode('utf-8')

                if 'Building documentation...' in line:
                    echo_waiting(line, nl=False)
                elif line.startswith(info_prefixes):
                    echo_info(line, nl=False)
                elif line.startswith(warning_prefixes):
                    echo_warning(line, nl=False)
                elif line.startswith(error_prefixes):
                    echo_failure(line, nl=False)
                else:
                    click.echo(line, nl=False)

                if not build_complete and line.rstrip().endswith(build_completion_indicator):
                    build_complete = True
                    if not no_open:
                        webbrowser.open_new_tab(address)

    abort(code=process.returncode)
