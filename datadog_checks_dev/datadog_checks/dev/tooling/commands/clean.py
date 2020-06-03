# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from ...utils import basepath, dir_exists, resolve_path
from ..clean import DELETE_EVERYWHERE, DELETE_IN_ROOT, clean_package, remove_compiled_scripts
from ..constants import get_root
from ..utils import complete_testable_checks
from .console import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help="Remove a project's build artifacts")
@click.argument('check', autocompletion=complete_testable_checks, required=False)
@click.option(
    '--compiled-only', '-c', is_flag=True, help=f"Remove compiled files only ({', '.join(sorted(DELETE_EVERYWHERE))})."
)
@click.option(
    '--all',
    '-a',
    'all_matches',
    is_flag=True,
    help=(
        "Disable the detection of a project's dedicated virtual "
        'env and/or editable installation. By default, these will '
        'not be considered.'
    ),
)
@click.option(
    '--force',
    '-f',
    is_flag=True,
    help=(
        f'If set and the command is run from the root directory, '
        f'allow removing build and test artifacts ({", ".join(sorted(DELETE_IN_ROOT))}).'
    ),
)
@click.option('--verbose', '-v', is_flag=True, help='Shows removed paths.')
@click.pass_context
def clean(ctx, check, compiled_only, all_matches, force, verbose):
    """Remove build and test artifacts for the given CHECK.
    If CHECK is not specified, the current working directory is used.
    """
    if check:
        path = resolve_path(os.path.join(get_root(), check))
        if not dir_exists(path):
            abort(
                'Directory `{}` does not exist. Be sure to `ddev config set {repo} '
                'path/to/integrations-{repo}`.'.format(path, repo=ctx.obj['repo_choice'])
            )
    else:
        path = os.getcwd()

    if compiled_only:
        echo_waiting(f'Cleaning compiled artifacts in `{path}`...')
        removed_paths = remove_compiled_scripts(path, detect_project=not all_matches)
    else:
        force_clean_root = False
        target_description = 'artifacts'

        if force:
            force_clean_root = True
            target_description = 'all artifacts'
        elif basepath(path) in ('integrations-core', 'integrations-extras'):
            echo_warning(
                'You are running this from the root of the integrations project.\n'
                'By default, the following artifacts in the root directory will *not* be cleaned:'
            )
            echo_info(', '.join(DELETE_IN_ROOT))
            force_clean_root = click.confirm(
                'Should we clean the above artifacts too? (Use --force of -f to bypass this prompt)'
            )

            if force_clean_root:
                target_description = 'all artifacts'
            else:
                target_description = 'artifacts (excluding those listed above)'

        echo_waiting(f'Cleaning {target_description} in `{path}`...')
        removed_paths = clean_package(path, detect_project=not all_matches, force_clean_root=force_clean_root)

    if verbose:
        if removed_paths:
            echo_success('Removed paths:')
            for p in removed_paths:
                echo_info(f'    {p}')

    if removed_paths:
        echo_success('Cleaned!')
    else:
        echo_success('Already clean!')
