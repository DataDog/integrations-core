# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

from datadog_checks.dev.subprocess import run_command


class TestRunCommand:
    def test_output(self):
        result = run_command(
            '{} -c "import sys;print(sys.version)"'.format(sys.executable),
            capture='out'
        )

        assert result.stdout.strip() == sys.version.strip()

    def test_env(self):
        env = dict(os.environ)
        env['DDEV_ENV_VAR'] = 'is_set'
        result = run_command(
            '{} -c "import os;print(os.getenv(\'DDEV_ENV_VAR\'))"'.format(sys.executable),
            capture='out',
            env=env
        )

        assert result.stdout.strip() == 'is_set'
