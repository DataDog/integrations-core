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


@pytest.mark.parametrize(
    'call, reported',
    [
        pytest.param('requests.Session()', 'requests.Session(', id='session'),
        pytest.param('requests.request("GET", url)', 'requests.request(', id='request'),
        pytest.param('requests.options(url)', 'requests.options(', id='options'),
    ],
)
def test_uses_requests_beyond_the_common_verbs(ddev, repository, helpers, call, reported):
    """A Session, a bare request or an options call re-couples an integration just as a get does."""
    check = 'apache'
    file_path = repository.path / check / 'datadog_checks' / check / 'apache.py'
    file_contents = file_path.read_text(encoding='utf-8').splitlines(keepends=True)

    file_contents[16] = f"    test={call}\n"
    file_path.write_text(''.join(file_contents), encoding='utf-8')

    result = ddev('validate', 'http', check)

    assert result.exit_code == 1, result.output
    assert f'Check `apache` uses `{reported}` in `apache.py`' in result.output


@pytest.mark.parametrize(
    'identifier',
    [
        pytest.param('def get_requests_data(self):', id='marklogic_shape'),
        pytest.param('def http_requests_total(self, metric):', id='kube_apiserver_metrics_shape'),
    ],
)
def test_identifier_merely_starting_with_requests_is_not_flagged(ddev, repository, helpers, identifier):
    """An identifier that merely begins with requests is not a call into the library."""
    check = 'apache'
    file_path = repository.path / check / 'datadog_checks' / check / 'apache.py'
    file_contents = file_path.read_text(encoding='utf-8').splitlines(keepends=True)

    file_contents[16] = f"    {identifier}\n        pass\n"
    file_path.write_text(''.join(file_contents), encoding='utf-8')

    result = ddev('validate', 'http', check)

    assert result.exit_code == 0, result.output
    assert 'please use the HTTP wrapper instead' not in result.output


def test_underscore_prefixed_client_still_requires_the_spec_templates(ddev, repository, helpers):
    """An integration that names its client self._http must not escape the spec.yaml template check."""
    import yaml

    check = 'apache'
    file_path = repository.path / check / 'datadog_checks' / check / 'apache.py'
    file_path.write_text(file_path.read_text(encoding='utf-8').replace('self.http', 'self._http'), encoding='utf-8')

    spec_yaml = repository.path / check / 'assets' / 'configuration' / 'spec.yaml'
    spec_info = yaml.safe_load(spec_yaml.read_text(encoding='utf-8'))
    spec_info['files'][0]['options'][0]['options'] = []
    spec_yaml.write_text(yaml.safe_dump(spec_info, default_flow_style=False, sort_keys=False), encoding='utf-8')

    result = ddev('validate', 'http', check)

    assert result.exit_code == 1, result.output
    assert 'missing `init_config/http`' in result.output


def test_skip_marker_does_not_disable_the_spec_templates(ddev, repository, helpers):
    """SKIP_HTTP_VALIDATION silences the parameter warning, not the whole integration's config check."""
    import yaml

    check = 'apache'
    file_path = repository.path / check / 'datadog_checks' / check / 'apache.py'
    file_contents = file_path.read_text(encoding='utf-8').splitlines(keepends=True)
    file_contents[16] = "    # SKIP_HTTP_VALIDATION\n"
    file_path.write_text(''.join(file_contents), encoding='utf-8')

    spec_yaml = repository.path / check / 'assets' / 'configuration' / 'spec.yaml'
    spec_info = yaml.safe_load(spec_yaml.read_text(encoding='utf-8'))
    spec_info['files'][0]['options'][0]['options'] = []
    spec_yaml.write_text(yaml.safe_dump(spec_info, default_flow_style=False, sort_keys=False), encoding='utf-8')

    result = ddev('validate', 'http', check)

    assert result.exit_code == 1, result.output
    assert 'missing `init_config/http`' in result.output


def test_shared_package_is_validated(ddev, repository, helpers):
    """datadog_checks_base has no manifest.json, so it is reached through the shippable predicate."""
    result = ddev('validate', 'http', 'datadog_checks_base')

    assert result.exit_code == 0, result.output
    assert 'Passed: 1' in result.output


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
