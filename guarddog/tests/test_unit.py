# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from unittest.mock import Mock

import pytest
from mock import ANY

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.guarddog import GuarddogCheck

dependency_file_path = "/tmp/dependency_file_path/requirements.txt"
package_ecosystem = "pypi"
MOCK_RESPONSE = [
    {
        "dependency": "flask",
        "version": "1.0.0",
        "result": {
            "issues": 1,
            "errors": {},
            "results": {
                "release_zero": "0.0.0",
            },
            "path": "/tmp/tmpmm2wc69i/flask",
        },
    },
    {
        "dependency": "requests",
        "version": "1.0.0",
        "result": {
            "issues": 1,
            "errors": {},
            "results": {
                "release_zero": "0.0.0",
            },
            "path": "/tmp/tmpmm2wc69i/requests",
        },
    },
    {
        "dependency": "pandas",
        "version": "1.0.0",
        "result": {
            "issues": 1,
            "errors": {},
            "results": {
                "release_zero": "0.0.0",
            },
            "path": "/tmp/tmpmm2wc69i/pandas",
        },
    },
]

EXPECTED_RESPONSE = [
    {
        'timestamp': ANY,
        'message': '{"log": {"dependency": "flask", "version": "1.0.0", '
        '"result": {"issues": 1, "errors": {}, "results": {"release_zero": "0.0.0"}, '
        '"path": "/tmp/tmpmm2wc69i/flask"}}, '
        '"enrichment_details": {"triggered_rules": ["release_zero"], '
        '"package_ecosystem": "pypi"}}',
    },
    {
        'timestamp': ANY,
        'message': '{"log": {"dependency": "requests", "version": "1.0.0", '
        '"result": {"issues": 1, "errors": {}, "results": {"release_zero": "0.0.0"}, '
        '"path": "/tmp/tmpmm2wc69i/requests"}}, '
        '"enrichment_details": {"triggered_rules": ["release_zero"], '
        '"package_ecosystem": "pypi"}}',
    },
    {
        'timestamp': ANY,
        'message': '{"log": {"dependency": "pandas", "version": "1.0.0", '
        '"result": {"issues": 1, "errors": {}, "results": {"release_zero": "0.0.0"}, '
        '"path": "/tmp/tmpmm2wc69i/pandas"}}, '
        '"enrichment_details": {"triggered_rules": ["release_zero"], '
        '"package_ecosystem": "pypi"}}',
    },
]


def test_instance_check(dd_run_check, aggregator, config, instance):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])

    assert isinstance(check, AgentCheck)


@pytest.mark.unit
def test_validate_configurations_with_empty_dependency_file_path(config, instance):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])

    empty_path = ""
    package_ecosystem = "pypi"
    err_message = (
        f"Dependency File Path is required for package ecosystem: {package_ecosystem} to run the guarddog scan"
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.package_ecosystem = package_ecosystem
        check.path = empty_path
        check.validate_config()


@pytest.mark.unit
def test_validate_configurations_with_nonexistent_dependency_file_path(config, instance):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])

    nonexistent_path = "/nonexistent/path/requirements.txt"
    check.package_ecosystem = "pypi"
    check.path = nonexistent_path
    err_message = f"Dependency file does not exist at the configured path: {nonexistent_path}"
    with pytest.raises(ConfigurationError, match=err_message):
        check.validate_config()


@pytest.mark.unit
def test_validate_configurations_with_unreadable_dependency_file_path(config, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])

    unreadable_path = "/unreadable/path/requirements.txt"
    check.package_ecosystem = "pypi"
    check.path = unreadable_path
    err_message = f"Dependency file not readable by agent: {unreadable_path}"

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=False)

    with pytest.raises(ConfigurationError, match=err_message):
        check.validate_config()


@pytest.mark.unit
def test_validate_configurations_with_empty_string_guarddog_path(config, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])

    err_message = "guarddog_path field should not be an empty string"

    # Mock Dependency File Checks
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)

    with pytest.raises(ConfigurationError, match=err_message):
        check.package_ecosystem = "pypi"
        check.path = "/path/to/dependency_file"
        check.guarddog_path = ""
        check.validate_config()


@pytest.mark.unit
def test_check_validate_config(config, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)

    assert check.validate_config() is None


@pytest.mark.unit
def test_get_guarddog_output(config, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])
    expected_stdout = "command output"
    expected_stderr = "command error"
    expected_returncode = 0
    check.package_ecosystem = "pypi"
    check.path = dependency_file_path
    cmd = "guarddog pypi verify /tmp/dependency_file_path/requirements.txt --output-format=json"

    mock_completed_process = Mock(stdout=expected_stdout, stderr=expected_stderr, returncode=expected_returncode)

    mocker.patch("subprocess.run", return_value=mock_completed_process)

    stdout = check.get_guarddog_output(cmd).stdout

    assert stdout == expected_stdout


@pytest.mark.unit
def test_check_guarddog_command_successful(config, datadog_agent, example_dependencies, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mock_stdout = json.dumps(
        MOCK_RESPONSE,
        separators=(",", ":"),
    )
    mock_stderr = ""
    mock_returncode = 0

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)

    mocker.patch(
        "subprocess.run", return_value=Mock(stdout=mock_stdout, stderr=mock_stderr, returncode=mock_returncode)
    )

    check.check(None)
    datadog_agent.assert_logs(check.check_id, EXPECTED_RESPONSE)

    mock_send_log = mocker.spy(check, "send_log")
    for call in mock_send_log.call_args_list:
        args, _ = call
        sent_data = args[0]
        assert json.loads(sent_data["message"])['log']["dependency"] in example_dependencies.split("\n")


@pytest.mark.unit
def test_check_guarddog_command_fails(config, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mocker.patch.object(check, "validate_config")
    mocker.patch("subprocess.run", return_value=Mock(stdout="", stderr="Error occurred", returncode=1))

    with pytest.raises(RuntimeError, match="Error occurred"):
        check.check(None)


@pytest.mark.unit
def test_check_guarddog_output_json_decode_error(config, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mocker.patch.object(check, "validate_config")
    mocker.patch("subprocess.run", return_value=Mock(stdout="Not a json", stderr="", returncode=0))

    with pytest.raises(json.JSONDecodeError):
        check.check(None)


@pytest.mark.unit
def test_check_abs_path_guarddog_not_found(config, datadog_agent, example_dependencies, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mocker.patch.object(check, "validate_config")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)
    mocker.patch(
        "subprocess.run",
        side_effect=[FileNotFoundError("Guarddog Not Found")],
    )
    with pytest.raises(FileNotFoundError):
        check.check(None)


@pytest.mark.unit
def test_check_both_guarddog_command_fails_with_not_found(config, instance, mocker):
    check = GuarddogCheck("guarddog", config['init_config'], [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mocker.patch.object(check, "validate_config")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)
    mocker.patch(
        "subprocess.run",
        side_effect=[
            FileNotFoundError("Guarddog Not Found"),
            FileNotFoundError("Guarddog Not Found"),
        ],
    )
    with pytest.raises(FileNotFoundError, match="Guarddog Not Found"):
        check.check(None)
