# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import yaml


def test_exactly_one_flag(ddev, repository, helpers):
    codecov_yaml = repository.path / '.codecov.yml'

    with codecov_yaml.open(encoding='utf-8') as file:
        codecov_yaml_info = yaml.safe_load(file)

    codecov_yaml_info['coverage']['status']['project']['ActiveMQ_XML']['flags'].append('test')

    output = yaml.safe_dump(codecov_yaml_info, default_flow_style=False, sort_keys=False)
    with codecov_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev("validate", "ci")

    assert result.exit_code == 1, result.output
    error = "Project `ActiveMQ_XML` must have exactly one flag"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_carryforward_flag(ddev, repository, helpers):
    codecov_yaml = repository.path / '.codecov.yml'

    with codecov_yaml.open(encoding='utf-8') as file:
        temp = yaml.safe_load(file)

    temp['flags']['active_directory']['carryforward'] = False

    output = yaml.safe_dump(temp, default_flow_style=False, sort_keys=False)
    with codecov_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev("validate", "ci")

    assert result.exit_code == 1, result.output
    error = "Flag `active_directory` must have carryforward set to true"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_missing_hatch_toml(ddev, repository, helpers):
    import os

    check = 'apache'
    hatch_file = repository.path / check / 'hatch.toml'
    os.remove(hatch_file)
    result = ddev("validate", "ci")

    assert result.exit_code == 1, result.output
    error = "CI configuration is not in sync, try again with the `--sync` flag"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_incorrect_project_name(ddev, repository, helpers):
    codecov_yaml = repository.path / '.codecov.yml'
    with codecov_yaml.open(encoding='utf-8') as file:
        codecov_yaml_info = yaml.safe_load(file)

    temp = codecov_yaml_info['coverage']['status']['project']['Active_Directory']
    codecov_yaml_info['coverage']['status']['project']['active directory'] = temp
    codecov_yaml_info['coverage']['status']['project'].pop('Active_Directory')

    output = yaml.safe_dump(codecov_yaml_info, default_flow_style=False, sort_keys=False)
    with codecov_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, result.output
    error = "Project `active directory` should be called `Active_Directory`"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_check_in_multiple_projects(ddev, repository, helpers):
    codecov_yaml = repository.path / '.codecov.yml'
    with codecov_yaml.open(encoding='utf-8') as file:
        codecov_yaml_info = yaml.safe_load(file)

    codecov_yaml_info['coverage']['status']['project']['Airflow']['flags'] = ['active_directory']

    output = yaml.safe_dump(codecov_yaml_info, default_flow_style=False, sort_keys=False)
    with codecov_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, result.output
    error = "Check `active_directory` is defined as a flag in more than one project"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_codecov_missing_projects(ddev, repository, helpers):
    codecov_yaml = repository.path / '.codecov.yml'
    with codecov_yaml.open(encoding='utf-8') as file:
        codecov_yaml_info = yaml.safe_load(file)

    codecov_yaml_info['coverage']['status']['project'].pop('Apache')

    output = yaml.safe_dump(codecov_yaml_info, default_flow_style=False, sort_keys=False)
    with codecov_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, result.output
    error = "Codecov config has 1 missing project"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_incorrect_coverage_source_path(ddev, repository, helpers):
    codecov_yaml = repository.path / '.codecov.yml'
    with codecov_yaml.open(encoding='utf-8') as file:
        codecov_yaml_info = yaml.safe_load(file)

    codecov_yaml_info['flags']['active_directory']['paths'] = [
        'active_directory/datadog_checks/test',
        'active_directory/tests',
    ]

    output = yaml.safe_dump(codecov_yaml_info, default_flow_style=False, sort_keys=False)
    with codecov_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, result.output
    error = "Flag `active_directory` has incorrect coverage source paths"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_codecov_missing_flag(ddev, repository, helpers):
    codecov_yaml = repository.path / '.codecov.yml'
    with codecov_yaml.open(encoding='utf-8') as file:
        codecov_yaml_info = yaml.safe_load(file)

    codecov_yaml_info['flags'].pop('active_directory')

    output = yaml.safe_dump(codecov_yaml_info, default_flow_style=False, sort_keys=False)
    with codecov_yaml.open(mode='w', encoding='utf-8') as file:
        file.write(output)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, result.output
    error = "Codecov config has 1 missing flag"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_validate_ci_success(ddev, repository, helpers):
    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        CI configuration validation

        Passed: 1
        """
    )
