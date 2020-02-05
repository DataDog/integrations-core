# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import subprocess

import click

from datadog_checks.dev.tooling.constants import get_root
from datadog_checks.dev.tooling.testing import get_tox_envs

from ..console import CONTEXT_SETTINGS

PLATFORM = platform.system().lower()
SCRIPTS_PATH = os.path.join(get_root(), '.azure-pipelines', 'scripts')


def display_action(script_file):
    display_header = f'Running: {script_file}'
    print(f'\n{display_header}\n{"-" * len(display_header)}\n')


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Run CI setup scripts')
@click.argument('checks', nargs=-1)
@click.option('--changed', is_flag=True, help='Only target changed checks')  # Added for compatibility with `ddev test`
def setup(checks, changed):
    """
    Run CI setup scripts
    """
    print("Run CI setup scripts")
    if checks:
        if checks[0] == 'skip':
            print('Skipping set up')
        else:
            print(f'Checks chosen: {repr(checks).strip("[]")}')
    else:
        print(f'Checks chosen: changed')

    check_envs = get_tox_envs(checks, every=True, sort=True, changed_only=changed)

    for check, _ in check_envs:
        scripts_path = os.path.join(SCRIPTS_PATH, check)

        if not os.path.isdir(scripts_path):
            print(f"Skip! No scripts for check `{check}` at: `{scripts_path}`")
            continue

        contents = os.listdir(scripts_path)

        if PLATFORM not in contents:
            print(f"Skip! No scripts for check `{check}` and platform `{PLATFORM}`")
            continue

        print(f'Setting up: {check}')
        scripts_path = os.path.join(scripts_path, PLATFORM)
        scripts = sorted(os.listdir(scripts_path))

        for script in scripts:
            script_file = os.path.join(scripts_path, script)
            display_action(script_file)
            subprocess.run([script_file], shell=True, check=True)
