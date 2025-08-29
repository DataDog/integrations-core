# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest  # noqa: I001

from datadog_checks.base import AgentCheck, ConfigurationError  # noqa: F401
from datadog_checks.mac_audit_logs import MacAuditLogsCheck, constants, utils

audit_logs_dir_path = "/var/audit/"
file_names = [
    "20230401000000.20230401120000",
    "20230401120000.20230401123045",
    "20230401123045.crash_recovery",
    "20230401123047.crash_recovery",
    "20230401123056.not_terminated",
    "20230401123058.not_terminated",
    "current",
]

file_names1 = [
    (utils.time_string_to_datetime_utc("20230401000000"), "20230401000000.20230401000001"),
    (utils.time_string_to_datetime_utc("20230401000001"), "20230401000001.not_terminated"),
]
log_cursor = {
    "record_time": "20230401000001",
    "file_name": "20230401000001.not_terminated",
    "record_milli_sec": " + 244 msec",
    "is_file_collection_completed": False,
}


def test_instance_check(dd_run_check, aggregator, instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    assert isinstance(check, AgentCheck)


@pytest.mark.unit
def test_validate_configurations_with_wrong_monitor_value(instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    wrong_monitor_value = "test"
    err_message = (
        f"The provided 'MONITOR' value '{wrong_monitor_value}' is not a valid boolean. "
        "Please provide either 'true' or 'false'."
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.monitor = wrong_monitor_value
        check.validate_configurations()


@pytest.mark.unit
def test_validate_configurations_with_wrong_min_collection_interval(instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    wrong_interval = -10
    err_message = (
        f"'min_collection_interval' must be a positive integer in range of {constants.MIN_COLLECTION_INTERVAL}"
        f" to {constants.MAX_COLLECTION_INTERVAL}, got {wrong_interval}."
    )
    with pytest.raises(ConfigurationError, match=err_message):
        check.min_collection_interval = wrong_interval
        check.validate_configurations()


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.utils.datetime")
def test_get_utc_timestamp_minus_hours(mock_datetime):
    mock_current_time = datetime(2023, 5, 11, 12, 0, 0, 234567, tzinfo=timezone.utc)
    mock_datetime.now.return_value = mock_current_time
    hours_offset = 5
    expected_timestamp = (mock_current_time - timedelta(hours=hours_offset)).strftime(constants.FILE_TIMESTAMP_FORMAT)

    # Call the function with the known current time
    actual_timestamp = utils.get_utc_timestamp_minus_hours(hours_offset)

    # Compare the actual timestamp with the expected timestamp
    assert actual_timestamp == expected_timestamp


@pytest.mark.unit
def test_time_string_to_datetime_utc():
    time_string = "20250604120000"  # Example time string in the format "%Y%m%d%H%M%S"
    expected_datetime = datetime(2025, 6, 4, 12, 00, 00, tzinfo=timezone.utc)

    actual_datetime = utils.time_string_to_datetime_utc(time_string)

    assert actual_datetime == expected_datetime


@pytest.mark.unit
def test_parse_timezone_offset():
    tz_offset = "+0530"
    expected_value = timedelta(hours=5, minutes=30)
    result = utils._parse_timezone_offset(tz_offset)

    assert result == expected_value


@pytest.mark.unit
def test_convert_utc_to_local_timezone_timestamp_str():
    utc_time = "20250604120000"
    tz_offset = "+0530"
    expected_local_time_str = "20250604173000"
    result_local_time_str = utils.convert_utc_to_local_timezone_timestamp_str(utc_time, tz_offset)

    assert result_local_time_str == expected_local_time_str


@pytest.mark.unit
def test_get_datetime_aware():
    date_str = "Wed Jun  4 12:00:00 2025"
    tz_offset = "+0530"
    expected_dt = datetime(2025, 6, 4, 12, 00, 00, tzinfo=timezone(timedelta(hours=5, minutes=30)))

    result_dt = utils.get_datetime_aware(date_str, tz_offset)

    assert result_dt == expected_dt


@pytest.mark.unit
def test_convert_local_to_utc_timezone_timestamp_str():
    time_str = "Wed Jun  4 17:30:00 2025"
    tz_offset = "+0530"
    expected_utc_time_str = "20250604120000"

    result_utc_str = utils.convert_local_to_utc_timezone_timestamp_str(time_str, tz_offset)

    assert result_utc_str == expected_utc_time_str


@pytest.mark.unit
@patch("os.path.isdir", return_value=True)
@patch('os.listdir', return_value=file_names)
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_collect_relevant_files(mock_listdir, mock_isdir, utc_timestamp_minus_hours, instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    # Call the method
    result = check.collect_relevant_files("20230401120000")

    # Define expected results
    expected = [
        (utils.time_string_to_datetime_utc("20230401000000"), "20230401000000.20230401120000"),
        (utils.time_string_to_datetime_utc("20230401120000"), "20230401120000.20230401123045"),
        (utils.time_string_to_datetime_utc("20230401123045"), "20230401123045.crash_recovery"),
        (utils.time_string_to_datetime_utc("20230401123047"), "20230401123047.crash_recovery"),
        (utils.time_string_to_datetime_utc("20230401123056"), "20230401123056.not_terminated"),
        (utils.time_string_to_datetime_utc("20230401123058"), "20230401123058.not_terminated"),
    ]
    # Check if the result matches the expected output
    assert result == expected


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.validate_configurations", return_value=None)
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.get_log_cursor", return_value=log_cursor)
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.collect_relevant_files", return_value=file_names1)
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.collect_data_from_files", return_value=None)
@patch("subprocess.run")
def test_collect_relevant_files_for_failed_last_iteration(
    mack_validate_config,
    mock_get_cursor,
    utc_timestamp_minus_hours,
    mock_relevent_files,
    mock_collect_data,
    mock_subprocess_run,
    instance,
):
    mac_audit_logs_check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    # Call the method
    mock_subprocess_run.return_value = MagicMock(stdout='+0530\n')
    mac_audit_logs_check.log = MagicMock()
    _ = mac_audit_logs_check.check(None)
    expected_files = [
        (utils.time_string_to_datetime_utc("20230401000001"), "20230401000001.not_terminated"),
    ]
    mac_audit_logs_check.log.debug.assert_called_with(
        f"Found the same file as the last failed iteration, relevant files: {expected_files}"
    )


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_get_previous_iteration_log_cursor_when_cusror_is_none(utc_timestamp_minus_hours, instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    last_record_time, last_record_milli_sec, last_collected_file_name = check.get_previous_iteration_log_cursor(None)

    # Check if the result matches the expected output
    assert last_record_time == "20230401000000"
    assert last_record_milli_sec is None
    assert last_collected_file_name is None


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_get_previous_iteration_log_cursor_when_cusror_is_not_none(utc_timestamp_minus_hours, instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    previous_cursor = {
        "record_time": "20230401000000",
        "record_milli_sec": " + 430 msec",
        "file_name": "20230401000000.20230401000015",
    }
    last_record_time, last_record_milli_sec, last_collected_file_name = check.get_previous_iteration_log_cursor(
        previous_cursor
    )

    # Check if the result matches the expected output
    assert last_record_time == "20230401000000"
    assert last_record_milli_sec == " + 430 msec"
    assert last_collected_file_name == "20230401000000.20230401000015"


@patch('datadog_checks.mac_audit_logs.check.subprocess.Popen')
def test_fetch_audit_logs(mock_popen, instance):
    logs = (
        "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 244 msec\" > /></record>\n<record time=\"Thu Jun  5 "
        "13:51:39 2025\" msec=\" + 154 msec\" > /></record>"
    )
    log_file_entries = logs.split("\n")
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    # Create a mock for the stdout and stderr data
    mock_auditreduce_stdout = MagicMock()
    mock_auditreduce_process = MagicMock(stdout=mock_auditreduce_stdout)
    mock_praudit_process = MagicMock(communicate=MagicMock(return_value=(logs, "")))

    # Set up the mock Popen objects
    mock_popen.side_effect = [mock_auditreduce_process, mock_praudit_process]

    # Call the method
    file_path = "/var/audit/20250605082138.20250605082142"
    time_filter_arg = "20250605132138"
    output, error = check.fetch_audit_logs(file_path, time_filter_arg)

    # Check that Popen was called with the correct arguments
    mock_popen.assert_any_call(
        f"sudo auditreduce -a {time_filter_arg} {file_path}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "TZ": "UTC"},
    )
    mock_popen.assert_any_call(
        'sudo praudit -xsl', shell=True, stdin=mock_auditreduce_stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Check the communicate method was called
    mock_praudit_process.communicate.assert_called_once()

    # Define expected results
    expected_output = logs
    log_entries = output.split("\n")
    expected_error = ""

    # Check if the result matches the expected output
    assert output == expected_output
    assert error == expected_error
    assert len(log_entries) == len(log_file_entries)


@patch.object(MacAuditLogsCheck, 'send_log')
def test_process_and_ingest_log_entries_skipping_logs_milli_seconds(mock_send_log, instance):
    logs = (
        "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 244 msec\" > /></record>\n<record time=\"Thu Jun  5 "
        "13:51:38 2025\" msec=\" + 278 msec\" > /></record>\n<record time=\"Thu Jun  5 13:51:42 2025\" "
        "msec=\" + 124 msec\" > /></record>"
    )
    log_entries = logs.split("\n")
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    check.process_and_ingest_log_entries(log_entries, "20250605082138.20250605082142", "+0000", " + 278 msec")
    assert mock_send_log.call_count == 2
