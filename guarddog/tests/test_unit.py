# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from unittest.mock import Mock

import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.guarddog import GuarddogCheck

dependency_file_path = "/tmp/dependency_file_path/requirements.txt"
package_ecosystem = "pypi"


def test_instance_check(dd_run_check, aggregator, instance):
    check = GuarddogCheck("guarddog", {}, [instance])

    assert isinstance(check, AgentCheck)


@pytest.mark.unit
def test_validate_configurations_with_wrong_package_ecosystem(instance):
    check = GuarddogCheck("guarddog", {}, [instance])

    wrong_package_ecosystem = "test"
    err_message = f"Invalid Package Ecosystem provided: {wrong_package_ecosystem}"
    with pytest.raises(ConfigurationError, match=err_message):
        check.package_ecosystem = wrong_package_ecosystem
        check.validate_config()


@pytest.mark.unit
def test_validate_configurations_with_empty_dependency_file_path(instance):
    check = GuarddogCheck("guarddog", {}, [instance])

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
def test_validate_configurations_with_nonexistent_dependency_file_path(instance):
    check = GuarddogCheck("guarddog", {}, [instance])

    nonexistent_path = "/nonexistent/path/requirements.txt"
    check.package_ecosystem = "pypi"
    check.path = nonexistent_path
    err_message = f"Dependency file does not exist at the configured path: {nonexistent_path}"
    with pytest.raises(ConfigurationError, match=err_message):
        check.validate_config()


@pytest.mark.unit
def test_validate_configurations_with_unreadable_dependency_file_path(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])

    unreadable_path = "/unreadable/path/requirements.txt"
    check.package_ecosystem = "pypi"
    check.path = unreadable_path
    err_message = f"Dependency file not readable by agent: {unreadable_path}"

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=False)

    with pytest.raises(ConfigurationError, match=err_message):
        check.validate_config()


@pytest.mark.unit
def test_check_validate_config(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)

    assert check.validate_config() is None


@pytest.mark.unit
def test_get_guarddog_output(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])
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
def test_check_guarddog_command_successful(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mock_stdout = json.dumps([{"result": {"results": {"rule1": True, "rule2": False}}}], separators=(",", ":"))
    mock_stderr = ""
    mock_returncode = 0

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)

    mocker.patch(
        "subprocess.run", return_value=Mock(stdout=mock_stdout, stderr=mock_stderr, returncode=mock_returncode)
    )

    mock_send_log = mocker.patch.object(check, "send_log")

    check.check(None)

    mock_send_log.assert_called_once()

    args, _ = mock_send_log.call_args
    sent_data = args[0]

    assert json.loads(sent_data["message"])["enrichment_details"]["triggered_rules"] == ["rule1"]


@pytest.mark.unit
def test_check_guarddog_command_fails(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mocker.patch.object(check, "validate_config")
    mocker.patch("subprocess.run", return_value=Mock(stdout="", stderr="Error occurred", returncode=1))

    with pytest.raises(RuntimeError, match="Error occurred"):
        check.check(None)


@pytest.mark.unit
def test_check_guarddog_output_json_decode_error(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mocker.patch.object(check, "validate_config")
    mocker.patch("subprocess.run", return_value=Mock(stdout="Not a json", stderr="", returncode=0))

    with pytest.raises(json.JSONDecodeError):
        check.check(None)


@pytest.mark.unit
def test_check_abs_path_guarddog_not_found(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mocker.patch.object(check, "validate_config")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)
    mock_stdout = json.dumps([{"result": {"results": {"rule1": True, "rule2": False}}}], separators=(",", ":"))
    mock_stderr = ""
    mock_returncode = 0
    mocker.patch(
        "subprocess.run",
        side_effect=[
            FileNotFoundError("Guarddog Not Found"),  # First call raises FileNotFoundError
            Mock(stdout=mock_stdout, stderr=mock_stderr, returncode=mock_returncode),  # Second call succeeds
        ],
    )
    mock_send_log = mocker.patch.object(check, "send_log")
    check.check(None)
    mock_send_log.assert_called_once()
    args, _ = mock_send_log.call_args
    sent_data = args[0]
    assert json.loads(sent_data["message"])["enrichment_details"]["triggered_rules"] == ["rule1"]


@pytest.mark.unit
def test_check_both_guarddog_command_fails(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])
    check.package_ecosystem = "pypi"
    check.path = "/path/to/dependency_file"
    mocker.patch.object(check, "validate_config")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.access", return_value=True)
    mocker.patch(
        "subprocess.run",
        side_effect=[
            FileNotFoundError("Guarddog Not Found"),  # First call raises FileNotFoundError
            Mock(stdout="", stderr="Error occurred", returncode="1"),  # Second call succeeds
        ],
    )
    with pytest.raises(RuntimeError, match="Error occurred"):
        check.check(None)


@pytest.mark.unit
def test_check_both_guarddog_command_fails_with_not_found(instance, mocker):
    check = GuarddogCheck("guarddog", {}, [instance])
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
