# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import pytest
from click.testing import CliRunner

from datadog_checks.dev import run_command


def _build_pyproject_file(authors):
    return f'''
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "datadog-my-check"
dynamic = ["version"]
authors = {authors}

[tool.hatch.version]
path = "datadog_checks/my_check/__about__.py"

[tool.hatch.build.targets.wheel]
include = ["/datadog_checks/my_check"]
'''


def _build_check(authors='[{ name = "Datadog", email = "packages@datadoghq.com" }]', license_file=False):
    os.mkdir('my_check')

    with open('my_check/pyproject.toml', 'w') as f:
        f.write(_build_pyproject_file(authors))

    os.makedirs('my_check/datadog_checks/my_check')
    with open('my_check/datadog_checks/my_check/__about__.py', 'w') as f:
        f.write('__version__ = "1.0.0"')

    if license_file:
        with open('my_check/LICENSE', 'w') as f:
            f.write('MIT License')


@pytest.mark.parametrize(
    'authors,expected_exit_code,expected_output',
    [
        ('[{ name = "Datadog", email = "packages@datadoghq.com" }]', 0, '1 valid'),
        ('[{ name = "Datadog"}]', 0, '1 valid'),
        ('[{ name = "Datadog", email = "invalid_email" }]', 1, 'Invalid email'),
    ],
)
def test_validate_package_validates_emails(authors, expected_exit_code, expected_output):
    runner = CliRunner()

    with runner.isolated_filesystem():
        _build_check(authors)

        result = run_command(
            [sys.executable, '-m', 'datadog_checks.dev', '-x', 'validate', 'package', 'my_check'],
            capture=True,
        )

        assert result.code == expected_exit_code
        assert expected_output in result.stdout


@pytest.mark.parametrize(
    'license_file,expected_exit_code,expected_output',
    [
        (False, 0, '1 valid'),
        (True, 1, 'Unexpected file in wheel: datadog_my_check-1.0.0.dist-info/licenses/LICENSE'),
    ],
)
def test_validate_package_validates_wheel_contents(license_file, expected_exit_code, expected_output):
    runner = CliRunner()

    with runner.isolated_filesystem():
        _build_check(license_file=license_file)

        result = run_command(
            [sys.executable, '-m', 'datadog_checks.dev', '-x', 'validate', 'package', 'my_check'],
            capture=True,
        )

        assert result.code == expected_exit_code
        assert expected_output in result.stdout
