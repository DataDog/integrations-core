# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from .utils import CONTEXT_SETTINGS, abort, echo_info, echo_success
from ..constants import get_root
from ..files import ALL_FILES
from ..utils import normalize_package_name


def display_files(files):
    for f in files:
        echo_info('    {}'.format(f.file_path))


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Create a new check')
@click.argument('check_name')
@click.option('--dry-run', '-n', is_flag=True)
@click.pass_context
def create(ctx, check_name, dry_run):
    """Create a new check."""
    check_name = normalize_package_name(check_name)

    check_dir = os.path.join(get_root(), check_name)
    if os.path.exists(check_name):
        abort('Path `{}` already exists!'.format(check_dir))

    config = {
        'root': check_dir,
        'check_name': check_name,
        'check_name_cap': check_name.capitalize(),
        'check_class': '{}Check'.format(''.join(part.capitalize() for part in check_name.split('_'))),
        'repo_choice': ctx.obj['repo_choice'],
    }

    files = sorted(
        (file(config) for file in ALL_FILES),
        key=lambda f: (-f.file_path.count(os.path.sep), f.file_path)
    )

    if dry_run:
        echo_success('Files:')
        display_files(files)
        return

    for f in files:
        f.write()

    echo_success('Files created:')
    display_files(files)
