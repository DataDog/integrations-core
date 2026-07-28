# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from ddev.utils.structures import EnvVars

if TYPE_CHECKING:
    from tests.helpers.git import ClonedRepo


@pytest.fixture(scope='module', autouse=True)
def terminal_width():
    with EnvVars({'COLUMNS': '200'}):
        yield


def _remove_apache_legacy_http_options_accesses(repository: ClonedRepo) -> None:
    apache_file = repository.path / 'apache' / 'datadog_checks' / 'apache' / 'apache.py'
    apache_file.write_text(apache_file.read_text(encoding='utf-8').replace('.options', '.config'), encoding='utf-8')


def test_warn_headers_auth(ddev, repository, helpers):
    check = 'apache'
    file_path = repository.path / check / 'datadog_checks' / check / 'apache.py'
    with file_path.open(encoding='utf-8') as file:
        file_contents = file.readlines()

    file_contents[16] = "    auth='test'"

    with file_path.open(mode='w', encoding='utf-8') as file:
        file.writelines(file_contents)

    result = ddev('validate', 'http', check)

    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        HTTP wrapper validation
        └── Apache

            The HTTP wrapper contains parameter `auth`, this configuration is handled by the wrapper automatically.
            If this a genuine usage of the parameters, please inline comment `# SKIP_HTTP_VALIDATION`

        Passed: 1
        Warnings: 1
        """
    )


def test_uses_requests(ddev, repository, helpers):
    check = 'apache'
    file_path = repository.path / check / 'datadog_checks' / check / 'apache.py'
    with file_path.open(encoding='utf-8') as file:
        file_contents = file.readlines()

    file_contents[16] = "    test=requests.get()"

    with file_path.open(mode='w', encoding='utf-8') as file:
        file.writelines(file_contents)

    result = ddev('validate', 'http', check)

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        HTTP wrapper validation
        └── Apache

            Check `apache` uses `requests.get(` in `apache.py`, please use the HTTP wrapper instead
            If this a genuine usage of the parameters, please inline comment `# SKIP_HTTP_VALIDATION`

        Errors: 1
        """
    )


def test_validate_http_ignores_legacy_options_outside_selection(ddev, repository):
    _remove_apache_legacy_http_options_accesses(repository)

    new_file = repository.path / 'airflow' / 'datadog_checks' / 'airflow' / 'legacy_options_probe.py'
    new_file.write_text("def probe(http):\n    http.options['timeout']\n", encoding='utf-8')

    result = ddev('validate', 'http', 'apache')

    assert result.exit_code == 0, result.output


def test_spec_missing_init_config(ddev, repository, helpers):
    check = 'apache'
    _remove_apache_legacy_http_options_accesses(repository)

    spec_yaml = repository.path / check / 'assets' / 'configuration' / 'spec.yaml'
    with spec_yaml.open(encoding='utf-8') as file:
        spec_info = yaml.safe_load(file)

    spec_info['files'][0]['options'][0]['options'] = []

    output = yaml.safe_dump(spec_info, default_flow_style=False, sort_keys=False)
    with spec_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev('validate', 'http', check)

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        HTTP wrapper validation
        └── Apache

            Detected apache is missing `init_config/http` or `init_config/openmetrics_legacy` template in spec.yaml

        Errors: 1
        """
    )


def test_spec_missing_instance(ddev, repository, helpers):
    check = 'apache'
    _remove_apache_legacy_http_options_accesses(repository)

    spec_yaml = repository.path / check / 'assets' / 'configuration' / 'spec.yaml'
    with spec_yaml.open(encoding='utf-8') as file:
        spec_info = yaml.safe_load(file)

    spec_info['files'][0]['options'][1]['options'] = spec_info['files'][0]['options'][1]['options'][0]

    output = yaml.safe_dump(spec_info, default_flow_style=False, sort_keys=False)
    with spec_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev('validate', 'http', check)

    assert result.exit_code == 1, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        HTTP wrapper validation
        └── Apache

            Detected apache is missing `instances/http` or `instances/openmetrics_legacy` template in spec.yaml

        Errors: 1
        """
    )


def test_validate_http_success(ddev, helpers):
    result = ddev('validate', 'http', 'apache', 'arangodb', 'zk')
    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        HTTP wrapper validation

        Passed: 3
        """
    )
