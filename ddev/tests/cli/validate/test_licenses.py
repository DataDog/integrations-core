# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import os

import pytest

from ddev.utils.toml import dump_toml_data, load_toml_file


@pytest.mark.parametrize(
    "name, contents, expected_error_output",
    [
        pytest.param(
            "licenses",
            {'dummy_package': 'dummy_license'},
            "EXPLICIT_LICENSES contains additional package not in agent",
            id="explicit licenses",
        ),
        pytest.param(
            "repo",
            {'dummy_package': 'https://github.com/dummy_package'},
            "PACKAGE_REPO_OVERRIDES contains additional package not in agent",
            id="package repo overrides",
        ),
    ],
)
def test_error_extra_dependency(name, contents, expected_error_output, ddev, repository, helpers):
    ddev_config_path = repository.path / '.ddev' / 'config.toml'

    data = load_toml_file(ddev_config_path)

    data['overrides']['dependencies'] = {name: contents}

    dump_toml_data(data, ddev_config_path)

    result = ddev('validate', 'licenses')

    assert result.exit_code == 1, result.output

    # Check if expected error validation error message is in output
    assert expected_error_output in helpers.remove_trailing_spaces(result.output)


@pytest.mark.parametrize(
    "repo, expected_message",
    [
        pytest.param("core", "Passed: 1", id="Core integrations"),
        pytest.param(
            "extras",
            "License validation is only available for repo `core`, skipping for repo `extras`",
            id="Extras integrations",
        ),
    ],
)
@pytest.mark.requires_ci
def test_validate_repo(repo, repository, expected_message, ddev, helpers, config_file):
    config_file.model.repo = repo
    config_file.save()

    result = ddev("validate", "licenses")

    assert expected_message in helpers.remove_trailing_spaces(result.output)


@pytest.mark.parametrize(
    "repo, expected_error_output",
    [
        pytest.param("core", "Requirements file is not found. Out of sync, run", id="Core integrations"),
    ],
)
def test_error_no_requirements_file(repo, repository, expected_error_output, ddev, helpers):
    agent_requirements_path = (
        repository.path / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in'
    )
    os.remove(agent_requirements_path)

    result = ddev("validate", "licenses")
    assert expected_error_output in helpers.remove_trailing_spaces(result.output)


@pytest.mark.parametrize(
    "repo, expected_error_output",
    [
        pytest.param(
            "core",
            "Detected InvalidRequirement error in agent_requirements.in:1 Expected end",
            id="Core integrations",
        ),
    ],
)
def test_invalid_requirement(repo, repository, expected_error_output, ddev, helpers):
    agent_requirements_path = (
        repository.path / 'datadog_checks_base' / 'datadog_checks' / 'base' / 'data' / 'agent_requirements.in'
    )

    with agent_requirements_path.open(encoding='utf-8') as file:
        requirements = file.readlines()

    requirements[0] = requirements[0].replace('==', '==^')

    with agent_requirements_path.open(mode='w', encoding='utf-8') as file:
        file.writelines(requirements[:3])

    result = ddev("validate", "licenses")

    assert expected_error_output in helpers.remove_trailing_spaces(result.output)
    assert 'aerospike==^4.0.0' in helpers.remove_trailing_spaces(result.output)
