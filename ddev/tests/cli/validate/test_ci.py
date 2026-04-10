# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import yaml


def test_missing_hatch_toml(ddev, repository, helpers):
    import os

    check = 'apache'
    hatch_file = repository.path / check / 'hatch.toml'
    os.remove(hatch_file)
    result = ddev("validate", "ci")

    assert result.exit_code == 1, result.output
    error = "CI configuration is not in sync, try again with the `--sync` flag"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_validate_ci_success(ddev, helpers):
    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        CI configuration validation

        Passed: 1
        """
    )


def test_code_coverage_missing_services(ddev, repository, helpers):
    config_path = repository.path / 'code-coverage.datadog.yml'
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config['services'] = [s for s in config.get('services', []) if s.get('id') != 'apache']

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, result.output
    error = "missing service"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_code_coverage_incorrect_paths(ddev, repository, helpers):
    config_path = repository.path / 'code-coverage.datadog.yml'
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    for service in config.get('services', []):
        if service.get('id') == 'active_directory':
            service['paths'] = ['wrong/path/']
            break

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, result.output
    error = "Service `active_directory` has incorrect coverage source paths"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_code_coverage_file_missing(ddev, repository, helpers, config_file):
    config_file.model.repos['core'] = str(repository.path)
    config_file.save()

    (repository.path / 'code-coverage.datadog.yml').unlink()

    result = ddev("-c", "validate", "ci")
    assert result.exit_code == 1, result.output
    assert "Unable to find the code coverage config file" in helpers.remove_trailing_spaces(result.output)


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
