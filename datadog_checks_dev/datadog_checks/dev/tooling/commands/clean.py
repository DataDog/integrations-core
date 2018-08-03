# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from .utils import (
    CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting, echo_warning
)
from ..utils import is_affirmative
from ..clean import clean_package, remove_compiled_scripts
from ..constants import get_root
from ...utils import dir_exists, resolve_path


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Remove a project's build artifacts"
)
@click.argument('check', required=False)
@click.option(
    '--compiled-only', '-c',
    is_flag=True,
    help='Removes only .pyc files.'
)
@click.option(
    '--all', '-a', 'all_matches',
    is_flag=True,
    help=(
        "Disable the detection of a project's dedicated virtual "
        'env and/or editable installation. By default, these will '
        'not be considered.'
    )
)
@click.option(
    '--force', '-f', 'force',
    is_flag=True,
    help=(
        "When run at the root of the project, "
        "it will ignore most build and testing artifacts, "
        "like .tox and build directories. "
        "Force it to remove these."
    )
)
@click.option('--verbose', '-v', is_flag=True, help='Shows removed paths.')
@click.pass_context
def clean(ctx, check, compiled_only, all_matches, verbose, force):
    """Removes a project's build artifacts.

    If `check` is not specified, the current working directory will be used.

    All `*.pyc`/`*.pyd`/`*.pyo`/`*.whl` files and `__pycache__` directories will be
    removed. Additionally, the following patterns will be removed from the root of
    the path: `.cache`, `.coverage`, `.eggs`, `.pytest_cache`, `.tox`, `build`,
    `dist`, and `*.egg-info`.
    """
    force_clean_root = False

    if check:
        path = resolve_path(os.path.join(get_root(), check))
        if not dir_exists(path):
            abort(
                'Directory `{}` does not exist. Be sure to `ddev config set {repo} '
                'path/to/integrations-{repo}`.'.format(path, repo=ctx.obj['repo_choice'])
            )
    else:
        path = os.getcwd()
        if path == resolve_path(get_root()):
            if force:
                force_clean_root = True
            else:
                echo_warning("You are running this from the root of the integrations project")
                echo_warning("Should we remove everything, including: ")
                echo_warning(".cache, .coverage, .eggs, .pytest_cache, .tox, build, dist, and *.egg-info")
                echo_warning("You can also use --force or -f to bypass this input")
                input = raw_input()
                if is_affirmative(input):
                    force_clean_root = True

    echo_waiting('Cleaning `{}`...'.format(path))
    if compiled_only:
        removed_paths = remove_compiled_scripts(path, detect_project=not all_matches)
    else:
        removed_paths = clean_package(path, detect_project=not all_matches, force_clean_root=force_clean_root)

    if verbose:
        if removed_paths:
            echo_success('Removed paths:')
            for p in removed_paths:
                echo_info('    {}'.format(p))

    if removed_paths:
        echo_success('Cleaned!')
    else:
        echo_success('Already clean!')
