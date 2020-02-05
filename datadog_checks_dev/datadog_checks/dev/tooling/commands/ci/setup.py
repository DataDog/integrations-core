# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import subprocess

import click

from ...constants import get_root
from ...testing import get_tox_envs
from ..console import CONTEXT_SETTINGS, echo_debug, echo_info


def display_action(script_file):
    display_header = f'Running: {script_file}'
    echo_info(f'\n{display_header}\n{"-" * len(display_header)}\n')


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Run CI setup scripts')
@click.argument('checks', nargs=-1)
@click.option('--changed', is_flag=True, help='Only target changed checks')
def setup(checks, changed):
    """
    Run CI setup scripts
    """
    cur_platform = platform.system().lower()
    scripts_path = os.path.join(get_root(), '.azure-pipelines', 'scripts')
    echo_info("Run CI setup scripts")
    if checks:
        if checks[0] == 'skip':
            echo_info('Skipping set up')
        else:
            echo_info(f'Checks chosen: {", ".join(checks)}')
    else:
        echo_info(f'Checks chosen: changed')

    check_envs = get_tox_envs(checks, every=True, sort=True, changed_only=changed)

    for check, _ in check_envs:
        scripts_path = os.path.join(scripts_path, check)

        if not os.path.isdir(scripts_path):
            echo_debug(f"Skip! No scripts for check `{check}` at: `{scripts_path}`")
            continue

        contents = os.listdir(scripts_path)

        if cur_platform not in contents:
            echo_debug(f"Skip! No scripts for check `{check}` and platform `{cur_platform}`")
            continue

        echo_info(f'Setting up: {check}')
        scripts_path = os.path.join(scripts_path, cur_platform)
        scripts = sorted(os.listdir(scripts_path))

        for script in scripts:
            script_file = os.path.join(scripts_path, script)
            display_action(script_file)
            subprocess.run([script_file], shell=True, check=True)
