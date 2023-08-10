# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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
    warning = 'The HTTP wrapper contains parameter `auth`, this configuration is'
    assert warning in helpers.remove_trailing_spaces(result.output)


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
    error = 'Check `apache` uses `requests.get(` in `apache.py`,'
    assert error in helpers.remove_trailing_spaces(result.output)


def test_spec_missing_info_config(ddev, repository, helpers):
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
    error = 'Detected apache is missing `init_config/http` or'
    assert error in helpers.remove_trailing_spaces(result.output)


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
    error = 'Detected apache is missing `instances/http` or'
    assert error in helpers.remove_trailing_spaces(result.output)


def test_validate_http_success(ddev, repository, helpers):
    result = ddev('validate', 'http', 'apache', 'arangodb', 'zk')
    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        Validating 3 integrations for usage of http wrapper...
        HTTP wrapper validation

        Passed: 1
        Completed http validation!
        """
    )

