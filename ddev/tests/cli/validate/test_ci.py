# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
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


# TODO We do not have an off the shelf fixture to generate a marketplace repository
@pytest.mark.parametrize(
    'repository_name, repository_flag, expected_exit_code, expected_output',
    [
        pytest.param('core', '-c', 1, 'Unable to find the Codecov config file', id='integrations-core'),
    ],
)
def test_codecov_file_missing(
    ddev, repository, helpers, config_file, repository_name, repository_flag, expected_exit_code, expected_output
):
    config_file.model.repos[repository_name] = str(repository.path)
    config_file.save()

    (repository.path / '.codecov.yml').unlink()

    result = ddev(repository_flag, "validate", "ci")
    assert result.exit_code == expected_exit_code, result.output
    assert expected_output in helpers.remove_trailing_spaces(result.output)


def test_validate_ci_success(ddev, helpers):
    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        CI configuration validation

        Passed: 1
        """
    )


@pytest.mark.parametrize(
    'repo_name',
    [
        pytest.param('core', id='core'),
        pytest.param('extras', id='extras'),
        pytest.param('marketplace', id='marketplace'),
    ],
)
def test_minimum_base_package(ddev, repository, helpers, repo_name, config_file):
    config_file.model.repos[repo_name] = str(repository.path)
    config_file.model.repo = repo_name
    config_file.save()

    result = ddev('validate', 'ci', '--sync')
    assert result.exit_code == 0, result.output

    test_all = repository.path / '.github' / 'workflows' / 'test-all.yml'
    with test_all.open(encoding='utf-8') as file:
        test_all_yaml_info = yaml.safe_load(file)

    for job in test_all_yaml_info['jobs'].values():
        if repo_name == 'extras':
            assert 'minimum-base-package' not in job['with']
        else:
            assert '${{ inputs.minimum-base-package }}' == job['with']['minimum-base-package']

    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output
