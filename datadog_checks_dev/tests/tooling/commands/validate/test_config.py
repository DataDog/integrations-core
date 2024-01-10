# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import shutil
import sys

import pytest
from click.testing import CliRunner

from datadog_checks.dev import run_command


@pytest.mark.parametrize(
    'repo,expect_failure',
    [
        ("core", True),
        ("extras", False),
        ("marketplace", False),
        ("internal", False),
    ],
)
def test_validate_config_spec_file_mandatory_in_core(repo, expect_failure):
    runner = CliRunner()

    with runner.isolated_filesystem():

        # Generate the check structure
        working_repo = 'integrations-{}'.format(repo)
        shutil.copytree(
            os.path.dirname(os.path.realpath(__file__)) + "/data/my_check", "./{}/my_check".format(working_repo)
        )
        os.chdir(working_repo)
        os.remove("my_check/assets/configuration/spec.yaml")

        result = run_command(
            [sys.executable, '-m', 'datadog_checks.dev', '--here', 'validate', 'config', 'my_check'],
            capture=True,
        )

        if expect_failure:
            assert 1 == result.code
            assert 'Files with errors: 1' in result.stdout
        else:
            assert 0 == result.code

        assert 'Validating default configuration files for 1 checks...' in result.stdout
        assert 'my_check:' in result.stdout
        assert 'Did not find spec file' in result.stdout
        assert '' == result.stderr
