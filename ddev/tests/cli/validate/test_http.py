# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.utils.structures import EnvVars


@pytest.fixture(scope='module', autouse=True)
def terminal_width():
    with EnvVars({'COLUMNS': '200'}):
        yield


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


def test_spec_missing_init_config(ddev, repository, helpers):
    import yaml

    check = 'apache'

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
    import yaml

    check = 'apache'

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
