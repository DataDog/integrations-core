# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import sys

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from ddev.integration.core import Integration
from ddev.utils import hatch
from ddev.utils.platform import Platform


@pytest.fixture
def mock_integration(mocker: MockerFixture) -> Integration:
    mock_integration = mocker.MagicMock(spec=Integration)
    mock_integration.path.as_cwd.return_value = mocker.MagicMock(
        __enter__=mocker.MagicMock(), __exit__=mocker.MagicMock(return_value=None)
    )
    mock_integration.name = "my-integration"
    return mock_integration


def platform(mocker: MockerFixture, output: str) -> Platform:
    platform = mocker.MagicMock(spec=Platform)
    platform.check_command_output.return_value = output
    return platform


def test_no_verbosity():
    assert not hatch.get_hatch_env_vars(verbosity=0)


def test_increased_verbosity():
    assert hatch.get_hatch_env_vars(verbosity=1) == {'HATCH_VERBOSE': '1'}


def test_decreased_verbosity():
    assert hatch.get_hatch_env_vars(verbosity=-1) == {'HATCH_QUIET': '1'}


def test_hatch_environment_configuration_from_dict():
    data = {
        "default": {
            "type": "virtual",
            "dependencies": ["dep1"],
            "test-env": True,
            "e2e-env": False,
            "benchmark-env": False,
            "latest-env": False,
        }
    }
    config = hatch.HatchEnvironmentConfiguration.model_validate(data)
    assert len(config.root) == 1
    env = config.root[0]
    assert env.name == "default"
    assert env.type == "virtual"
    assert env.dependencies == ["dep1"]
    assert env.test_env is True


def test_hatch_environment_configuration_from_list():
    data = [
        {
            "name": "default",
            "type": "virtual",
            "dependencies": ["dep1"],
            "test-env": True,
            "e2e-env": False,
            "benchmark-env": False,
            "latest-env": False,
        }
    ]
    config = hatch.HatchEnvironmentConfiguration.model_validate(data)
    assert len(config.root) == 1
    env = config.root[0]
    assert env.name == "default"


def test_hatch_environment_configuration_invalid_data():
    with pytest.raises(ValidationError):
        hatch.HatchEnvironmentConfiguration.model_validate("invalid")


def test_env_show_json(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, '{"key": "value"}')
    result = hatch.env_show(mock_platform, mock_integration, as_json=True)

    assert result == {"key": "value"}
    mock_platform.check_command_output.assert_called_once()
    cmd = mock_platform.check_command_output.call_args[0][0]
    assert '--json' in cmd


def test_env_show_string(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, 'some output')
    result = hatch.env_show(mock_platform, mock_integration, as_json=False)

    assert result == "some output"
    mock_platform.check_command_output.assert_called_once()
    cmd = mock_platform.check_command_output.call_args[0][0]
    assert '--json' not in cmd


def test_env_show_invalid_json(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, 'invalid json')
    with pytest.raises(hatch.HatchCommandError):
        hatch.env_show(mock_platform, mock_integration, as_json=True)


HATCH_OUTPUT = {
    "linux_e2e_no_python": {
        "type": "virtual",
        "dependencies": [],
        "test-env": True,
        "e2e-env": False,
        "benchmark-env": False,
        "latest-env": True,
        "platforms": ["linux"],
    },
    "no_platform_no_e2e_py3.8": {
        "type": "virtual",
        "dependencies": [],
        "test-env": True,
        "e2e-env": False,
        "benchmark-env": False,
        "latest-env": False,
        "python": "3.8",
    },
    "no_platform_e2e_no_python": {
        "type": "virtual",
        "dependencies": [],
        "test-env": False,
        "e2e-env": True,
        "benchmark-env": False,
        "latest-env": False,
    },
}


def test_list_environment_names_match_all(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, json.dumps(HATCH_OUTPUT))
    filters = [lambda environment: environment.test_env, lambda environment: "linux" in environment.platforms]

    names = hatch.list_environment_names(mock_platform, mock_integration, filters, match_all=True)

    assert names == ["linux_e2e_no_python"]


def test_list_environment_names_match_any(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, json.dumps(HATCH_OUTPUT))
    filters = [lambda environment: environment.e2e_env, lambda environment: environment.python == "3.8"]

    names = hatch.list_environment_names(mock_platform, mock_integration, filters, match_all=False)

    assert sorted(names) == sorted(["no_platform_no_e2e_py3.8", "no_platform_e2e_no_python"])


def test_list_environment_names_no_match(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, json.dumps(HATCH_OUTPUT))
    filters = [lambda environment: environment.benchmark_env]

    names = hatch.list_environment_names(mock_platform, mock_integration, filters)

    assert names == []


def test_list_environments_without_filters(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, json.dumps(HATCH_OUTPUT))
    environments = hatch.list_environments(mock_platform, mock_integration)

    assert len(environments) == 3
    assert sorted(env.name for env in environments) == sorted(
        ["linux_e2e_no_python", "no_platform_no_e2e_py3.8", "no_platform_e2e_no_python"]
    )


def test_remove_environment(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, json.dumps(HATCH_OUTPUT))
    hatch.remove_environment(mock_platform, mock_integration, "linux_e2e_no_python")

    mock_platform.check_command.assert_called_once_with(
        [sys.executable, '-m', 'hatch', 'env', 'remove', 'linux_e2e_no_python']
    )


def test_remove_environment_fails(mocker: MockerFixture, mock_integration: Integration):
    mock_platform = platform(mocker, json.dumps(HATCH_OUTPUT))
    mock_platform.check_command.side_effect = Exception("Failed to remove environment")

    with pytest.raises(hatch.HatchCommandError):
        hatch.remove_environment(mock_platform, mock_integration, "linux_e2e_no_python")
