# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

from datadog_checks.dev import EnvVars, run_command
from datadog_checks.dev.utils import chdir, remove_path
from datadog_checks.dev._env import TESTING_PLUGIN


HERE = os.path.dirname(os.path.abspath(__file__))
CORE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def test_new_check_test():
    check_path = os.path.join(CORE_ROOT, 'my_check')

    try:
        run_command(
            [sys.executable, '-m', 'datadog_checks.dev', 'create', '-q', '-l', CORE_ROOT, 'my-check'],
            capture=True,
            check=True
        )
        run_command(
            [sys.executable, '-m', 'pip', 'install', check_path],
            capture=True,
            check=True
        )

        with chdir(check_path):
            with EnvVars(ignore=[TESTING_PLUGIN]):
                run_command([sys.executable, '-m', 'pytest'], capture=True, check=True)

        run_command(
            [sys.executable, '-m', 'pip', 'uninstall', '-y', 'my-check'],
            capture=True,
            check=True
        )
    finally:
        remove_path(check_path)
