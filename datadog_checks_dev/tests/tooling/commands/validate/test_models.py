# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import shutil
import sys

import pytest
from click.testing import CliRunner

from datadog_checks.dev import run_command
from datadog_checks.dev.tooling.configuration.consumers.model.model_consumer import VALIDATORS_DOCUMENTATION
from datadog_checks.dev.tooling.utils import get_license_header


@pytest.mark.parametrize(
    'repo,expect_licenses',
    [
        ("core", True),
        ("extras", False),
    ],
)
def test_generate_new_files_check_licenses(repo, expect_licenses):
    runner = CliRunner()

    with runner.isolated_filesystem():

        # Generate the check structure
        working_repo = 'integrations-{}'.format(repo)
        shutil.copytree(
            os.path.dirname(os.path.realpath(__file__)) + "/data/my_check", "./{}/my_check".format(working_repo)
        )
        os.chdir(working_repo)

        result = run_command(
            [sys.executable, '-m', 'datadog_checks.dev', '--here', 'validate', 'models', 'my_check', "-s"],
            capture=True,
        )

        assert 0 == result.code
        assert 'All 5 data model files are in sync!' in result.stdout
        assert 5 == result.stdout.count("Writing data model file")

        for filename in os.listdir("my_check/datadog_checks/my_check/config_models"):
            if filename != ".gitkeep":
                with open(f"my_check/datadog_checks/my_check/config_models/{filename}", mode='r') as file:
                    assert expect_licenses == file.read().startswith(get_license_header())

        # Also validate that the validators.py is correctly generated
        with open("my_check/datadog_checks/my_check/config_models/validators.py", mode='r') as validators_file:
            if expect_licenses:
                assert validators_file.read() == get_license_header() + "\n\n" + VALIDATORS_DOCUMENTATION
            else:
                assert validators_file.read() == VALIDATORS_DOCUMENTATION
