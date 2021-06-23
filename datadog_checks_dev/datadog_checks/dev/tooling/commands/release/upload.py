# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from ....fs import basepath, chdir, dir_exists, resolve_path
from ....subprocess import run_command
from ...constants import get_root
from ...release import build_package
from ...utils import complete_valid_checks, get_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_success, echo_waiting


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Build and upload a check to PyPI')
@click.argument('check', autocompletion=complete_valid_checks)
@click.option('--sdist', '-s', is_flag=True)
@click.option('--dry-run', '-n', is_flag=True)
@click.pass_context
def upload(ctx, check, sdist, dry_run):
    """Release a specific check to PyPI as it is on the repo HEAD."""
    if check in get_valid_checks():
        check_dir = os.path.join(get_root(), check)
    else:
        check_dir = resolve_path(check)
        if not dir_exists(check_dir):
            abort(f'`{check}` is not an Agent-based Integration or Python package')

        check = basepath(check_dir)

    # retrieve credentials
    pypi_config = ctx.obj.get('pypi', {})
    username = pypi_config.get('user') or os.getenv('TWINE_USERNAME')
    password = pypi_config.get('pass') or os.getenv('TWINE_PASSWORD')
    if not (username and password):
        abort('This requires pypi.user and pypi.pass configuration. Please see `ddev config -h`.')

    auth_env_vars = {'TWINE_USERNAME': username, 'TWINE_PASSWORD': password}
    echo_waiting(f'Building and publishing `{check}` to PyPI...')

    with chdir(check_dir, env_vars=auth_env_vars):
        result = build_package(check_dir, sdist)
        if result.code != 0:
            abort(result.stdout, result.code)
        echo_waiting('Uploading the package...')
        if not dry_run:
            result = run_command(f'twine upload --skip-existing dist{os.path.sep}*')
            if result.code != 0:
                abort(code=result.code)

    echo_success('Success!')
