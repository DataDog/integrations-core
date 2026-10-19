# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

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


def _remove_service(config_path):
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config['services'] = [s for s in config.get('services', []) if s.get('id') != 'apache']

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _set_wrong_paths(config_path):
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    for service in config.get('services', []):
        if service.get('id') == 'active_directory':
            service['paths'] = ['wrong/path/']
            break

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _add_stale_service(config_path):
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config.setdefault('services', []).append({'id': 'stale_service', 'paths': ['stale_service/tests/']})

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _add_duplicate_service(config_path: Path) -> None:
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    duplicate_service = next(service for service in config['services'] if service.get('id') == 'active_directory')
    config['services'].append({'id': duplicate_service['id'], 'paths': list(duplicate_service['paths'])})

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _remove_gates(config_path: Path) -> None:
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config.pop('gates', None)

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _clear_gates(config_path: Path) -> None:
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config['gates'] = []

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


@pytest.mark.parametrize(
    'corrupt_config, expected_error',
    [
        pytest.param(_remove_service, "Code coverage config has 1 missing service", id='missing_services'),
        pytest.param(
            _set_wrong_paths,
            "Service `active_directory` has incorrect coverage source paths",
            id='incorrect_paths',
        ),
        pytest.param(
            _add_stale_service, "Code coverage config has 1 stale service: stale_service", id='stale_services'
        ),
        pytest.param(
            _add_duplicate_service,
            "Code coverage config has 1 duplicate service ID: active_directory",
            id='duplicate_services',
        ),
        pytest.param(_remove_gates, "Code coverage config has no coverage gates", id='missing_gates'),
        pytest.param(_clear_gates, "Code coverage config has no coverage gates", id='empty_gates'),
    ],
)
def test_code_coverage_config(ddev, repository, helpers, corrupt_config, expected_error):
    result = ddev("validate", "ci", "--sync")
    assert result.exit_code == 0, result.output

    config_path = repository.path / 'code-coverage.datadog.yml'
    corrupt_config(config_path)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, f"Expected validation to detect corrupted config: {result.output}"
    assert expected_error in helpers.remove_trailing_spaces(result.output)

    result = ddev("validate", "ci", "--sync")
    assert result.exit_code == 0, f"Expected --sync to fix corrupted config: {result.output}"

    result = ddev("validate", "ci")
    assert result.exit_code == 0, f"Expected validation to pass after sync: {result.output}"


def test_code_coverage_file_missing(ddev, repository, helpers):
    (repository.path / 'code-coverage.datadog.yml').unlink()

    result = ddev("-c", "validate", "ci")
    assert result.exit_code == 1, result.output
    assert "Unable to find the code coverage config file" in helpers.remove_trailing_spaces(result.output)


def test_code_coverage_skipped_for_extras(ddev, repository, helpers, config_file):
    config_file.model.repos['extras'] = str(repository.path)
    config_file.model.repo = 'extras'
    config_file.save()

    # Remove the coverage file entirely — extras should not care
    coverage_file = repository.path / 'code-coverage.datadog.yml'
    if coverage_file.exists():
        coverage_file.unlink()

    result = ddev('validate', 'ci', '--sync')
    assert result.exit_code == 0, result.output

    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output


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
