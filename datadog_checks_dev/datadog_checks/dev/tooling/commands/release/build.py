# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from ....utils import basepath, dir_exists, remove_path, resolve_path
from ...constants import get_root
from ...release import build_package
from ...utils import complete_testable_checks, get_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Build a wheel for a check')
@click.argument('check', autocompletion=complete_testable_checks)
@click.option('--sdist', '-s', is_flag=True)
def build(check, sdist):
    """Build a wheel for a check as it is on the repo HEAD"""
    if check in get_valid_checks():
        check_dir = os.path.join(get_root(), check)
    else:
        check_dir = resolve_path(check)
        if not dir_exists(check_dir):
            abort(f'`{check}` is not an Agent-based Integration or Python package')

        check = basepath(check_dir)

    echo_waiting(f'Building `{check}`...')

    dist_dir = os.path.join(check_dir, 'dist')
    remove_path(dist_dir)

    result = build_package(check_dir, sdist)
    if result.code != 0:
        abort(result.stdout, result.code)

    echo_info(f'Build done, artifact(s) in: {dist_dir}')
    echo_success('Success!')
