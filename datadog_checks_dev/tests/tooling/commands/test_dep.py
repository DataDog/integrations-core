# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import shutil
import sys

from click.testing import CliRunner

from datadog_checks.dev import run_command
from datadog_checks.dev.tooling.dependencies import read_check_dependencies


def test_freeze():

    with CliRunner().isolated_filesystem():

        # Generate the project structure
        shutil.copytree(os.path.dirname(os.path.realpath(__file__)) + "/data/my_repo", "./integrations-core")
        os.chdir("./integrations-core")

        result = run_command(
            [sys.executable, '-m', 'datadog_checks.dev', '--here', 'dep', 'freeze'],
            capture=True,
        )

        assert result.code == 0
