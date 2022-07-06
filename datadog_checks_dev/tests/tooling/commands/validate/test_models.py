# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import shutil

import pytest
from click.testing import CliRunner

from datadog_checks.dev.tooling.commands.validate import models
from datadog_checks.dev.tooling.config import copy_default_config
from datadog_checks.dev.tooling.utils import get_license_header, initialize_root


@pytest.mark.parametrize(
    'repo,expect_licenses',
    [
        ("core", True),
        ("extras", False),
    ],
)
def test_generate_new_files_check_licenses(repo, expect_licenses, reset_root):
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Generate the check structure
        shutil.copytree(os.path.dirname(os.path.realpath(__file__)) + "/data/my_check", "./my_check")

        result = runner.invoke(models, ["my_check", "-s"], obj=__get_config(repo))

        assert 0 == result.exit_code
        assert 'All 5 data model files are in sync!' in result.stdout
        assert 5 == result.stdout.count("Writing data model file")

        for filename in os.listdir("my_check/datadog_checks/my_check/config_models"):
            if filename != ".gitkeep":
                with open(f"my_check/datadog_checks/my_check/config_models/{filename}", mode='r') as file:
                    assert expect_licenses == file.read().startswith(get_license_header())


def __get_config(repo):
    config = copy_default_config()
    config["repo"] = repo
    config["repo_choice"] = repo
    config["repos"][repo] = os.getcwd()
    initialize_root(config)

    return config
