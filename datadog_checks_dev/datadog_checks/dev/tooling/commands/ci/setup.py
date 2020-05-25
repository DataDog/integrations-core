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
        echo_info('Checks chosen: changed')

    check_envs = list(get_tox_envs(checks, every=True, sort=True, changed_only=changed))
    echo_info(f'Configuring these envs: {check_envs}')

    for check, _ in check_envs:
        check_scripts_path = os.path.join(scripts_path, check)

        if not os.path.isdir(check_scripts_path):
            echo_debug(f"Skip! No scripts for check `{check}` at: `{check_scripts_path}`")
            continue

        contents = os.listdir(check_scripts_path)

        if cur_platform not in contents:
            echo_debug(f"Skip! No scripts for check `{check}` and platform `{cur_platform}`")
            continue

        scripts = sorted(os.listdir(os.path.join(check_scripts_path, cur_platform)))
        echo_info(f'Setting up: {check} with these config scripts: {scripts}')

        for script in scripts:
            script_file = os.path.join(check_scripts_path, cur_platform, script)
            display_action(script_file)
            cmd = [script_file]
            if script_file.endswith('.py'):
                cmd.insert(0, 'python')
            subprocess.run(cmd, shell=True, check=True)
