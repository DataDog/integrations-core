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


@pytest.mark.parametrize(
    'repo,expect_failure',
    [
        ("core", True),
        ("extras", False),
        ("marketplace", False),
        ("internal", False),
    ],
)
def test_validate_config_models_not_in_sync(repo, expect_failure):
    runner = CliRunner()

    with runner.isolated_filesystem():

        # Generate the check structure
        working_repo = 'integrations-{}'.format(repo)
        shutil.copytree(
            os.path.dirname(os.path.realpath(__file__)) + "/data/my_check", "./{}/my_check".format(working_repo)
        )
        os.chdir(working_repo)
        shutil.rmtree("my_check/datadog_checks/my_check/config_models")

        result = run_command(
            [sys.executable, '-m', 'datadog_checks.dev', '--here', 'validate', 'models', 'my_check'],
            capture=True,
        )

        if expect_failure:
            assert 1 == result.code
            assert 'Validating data models for 1 checks ...' in result.stdout
            assert 'File `__init__.py` is not in sync, run "ddev validate models my_check -s"' in result.stdout
            assert 'File `defaults.py` is not in sync, run "ddev validate models my_check -s"' in result.stdout
            assert 'File `instance.py` is not in sync, run "ddev validate models my_check -s"' in result.stdout
            assert 'File `shared.py` is not in sync, run "ddev validate models my_check -s"' in result.stdout
            assert 'File `validators.py` is not in sync, run "ddev validate models my_check -s"' in result.stdout
            assert '' == result.stderr
        else:
            assert 0 == result.code
            assert 'Validating data models for 1 checks ...' in result.stdout
            assert '' == result.stderr


@pytest.mark.parametrize(
    'repo,expect_failure',
    [
        ("core", False),
        ("extras", True),
        ("marketplace", True),
        ("internal", True),
    ],
)
def test_validate_no_config_models(repo, expect_failure):
    # Some integrations do not have config models, for instance tokumx because it's py2 only
    runner = CliRunner()

    with runner.isolated_filesystem():

        # Generate the check structure
        working_repo = 'integrations-{}'.format(repo)
        shutil.copytree(
            os.path.dirname(os.path.realpath(__file__)) + "/data/tokumx", "./{}/tokumx".format(working_repo)
        )
        os.chdir(working_repo)

        result = run_command(
            [sys.executable, '-m', 'datadog_checks.dev', '--here', 'validate', 'models', 'tokumx'],
            capture=True,
        )

        if expect_failure:
            assert 1 == result.code
            assert 'Validating data models for 1 checks ...' in result.stdout
            assert 'File `__init__.py` is not in sync, run "ddev validate models tokumx -s"' in result.stdout
            assert 'File `defaults.py` is not in sync, run "ddev validate models tokumx -s"' in result.stdout
            assert 'File `instance.py` is not in sync, run "ddev validate models tokumx -s"' in result.stdout
            assert 'File `shared.py` is not in sync, run "ddev validate models tokumx -s"' in result.stdout
            assert 'File `validators.py` is not in sync, run "ddev validate models tokumx -s"' in result.stdout
            assert '' == result.stderr
        else:
            assert 0 == result.code
            assert 'Validating data models for 1 checks ...' in result.stdout
            assert '' == result.stderr
