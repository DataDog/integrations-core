# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest  # noqa: I001

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.errors import ConfigurationError  # noqa: F401
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

closed_files1 = [
    (
        utils.time_string_to_datetime_utc("20230401000000"),
        utils.time_string_to_datetime_utc("20230401000001"),
        "20230401000000.20230401000001",
    ),
]
open_files1 = [
    (utils.time_string_to_datetime_utc("20230401000001"), "20230401000001.not_terminated"),
]
log_cursor = {
    "record_time": "20230401000001",
    "record_milli_sec": " + 244 msec",
    "is_file_collection_completed": False,
    "last_completed_closed": [],
    "last_completed_open": [],
}


@pytest.mark.unit
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
@patch("os.path.isfile", return_value=True)  # All entries are files
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_collect_relevant_files(mock_get_utc, mock_isfile, mock_listdir, mock_isdir, instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    closed, still_open = check.collect_relevant_files("20230401120000")

    expected_closed = [
        (
            utils.time_string_to_datetime_utc("20230401000000"),
            utils.time_string_to_datetime_utc("20230401120000"),
            "20230401000000.20230401120000",
        ),
        (
            utils.time_string_to_datetime_utc("20230401120000"),
            utils.time_string_to_datetime_utc("20230401123045"),
            "20230401120000.20230401123045",
        ),
    ]
    expected_still_open = [
        (utils.time_string_to_datetime_utc("20230401123045"), "20230401123045.crash_recovery"),
        (utils.time_string_to_datetime_utc("20230401123047"), "20230401123047.crash_recovery"),
        (utils.time_string_to_datetime_utc("20230401123056"), "20230401123056.not_terminated"),
        (utils.time_string_to_datetime_utc("20230401123058"), "20230401123058.not_terminated"),
    ]
    assert closed == expected_closed
    assert still_open == expected_still_open


@pytest.mark.unit
@patch("os.path.isdir", return_value=True)
@patch(
    'os.listdir',
    return_value=["20230401000000.20230401120000", "secure", "_hold", "some_dir", "current", "file.txt.bak"],
)
@patch("os.path.isfile", side_effect=lambda path: not path.endswith("some_dir"))  # some_dir is a directory
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_collect_relevant_files_with_non_standard_entries(
    mock_get_utc, mock_isfile, mock_listdir, mock_isdir, instance
):
    """Test that non-standard files and directories are skipped without errors."""
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    check.log = MagicMock()

    closed, still_open = check.collect_relevant_files("20230401120000")

    expected_closed = [
        (
            utils.time_string_to_datetime_utc("20230401000000"),
            utils.time_string_to_datetime_utc("20230401120000"),
            "20230401000000.20230401120000",
        ),
    ]
    assert closed == expected_closed
    assert still_open == []

    # Verify debug logging for skipped entries
    debug_calls = check.log.debug.call_args_list
    debug_messages = [str(call) for call in debug_calls]

    # Check that debug messages were logged for non-standard files
    assert any("secure" in msg for msg in debug_messages), "Should log debug for 'secure' file"
    assert any("_hold" in msg for msg in debug_messages), "Should log debug for '_hold' file"
    assert any("some_dir" in msg for msg in debug_messages), "Should log debug for directory"
    assert any("file.txt.bak" in msg for msg in debug_messages), "Should log debug for file with wrong format"

    # Ensure no error logs were generated
    check.log.error.assert_not_called()


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.validate_configurations", return_value=None)
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.get_log_cursor", return_value=log_cursor)
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
@patch(
    "datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.collect_relevant_files",
    return_value=(closed_files1, open_files1),
)
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.collect_data_from_files", return_value=None)
@patch("subprocess.run")
def test_collect_relevant_files_for_failed_last_iteration(
    mock_subprocess_run,
    mock_collect_data,
    mock_relevant_files,
    utc_timestamp_minus_hours,
    mock_get_cursor,
    mock_validate_config,
    instance,
):
    """When the previous cycle aborted partway through, the next cycle resumes from the file
    containing the last emitted record and continues forward through later files."""
    mac_audit_logs_check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    mock_subprocess_run.return_value = MagicMock(stdout='+0530\n')
    mac_audit_logs_check.log = MagicMock()
    mac_audit_logs_check.check(None)

    call_args = mock_collect_data.call_args
    narrowed_closed = call_args[0][0]
    narrowed_open = call_args[0][1]
    assert narrowed_closed == closed_files1
    assert narrowed_open == open_files1


_boundary_cursor = {
    "record_time": "20230401020000",
    "record_milli_sec": " + 100 msec",
    "is_file_collection_completed": False,
    "last_completed_closed": [],
    "last_completed_open": [],
}
_boundary_closed = [
    (
        utils.time_string_to_datetime_utc("20230401010000"),
        utils.time_string_to_datetime_utc("20230401020000"),
        "20230401010000.20230401020000",
    ),
    (
        utils.time_string_to_datetime_utc("20230401020000"),
        utils.time_string_to_datetime_utc("20230401030000"),
        "20230401020000.20230401030000",
    ),
    (
        utils.time_string_to_datetime_utc("20230401030000"),
        utils.time_string_to_datetime_utc("20230401040000"),
        "20230401030000.20230401040000",
    ),
]


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.validate_configurations", return_value=None)
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.get_log_cursor", return_value=_boundary_cursor)
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
@patch(
    "datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.collect_relevant_files",
    return_value=(_boundary_closed, []),
)
@patch("datadog_checks.mac_audit_logs.check.MacAuditLogsCheck.collect_data_from_files", return_value=None)
@patch("subprocess.run")
def test_resume_narrowing_picks_file_starting_at_cursor_record_time(
    mock_subprocess_run,
    mock_collect_data,
    mock_relevant_files,
    utc_timestamp_minus_hours,
    mock_get_cursor,
    mock_validate_config,
    instance,
):
    """When the last emitted record's timestamp coincides exactly with the
    start of a new audit file, resuming an aborted cycle reads forward from
    that new file (and any files after it), not from the file whose end
    matches the timestamp. Reading from the older file would re-process
    records that were already emitted in the prior cycle.
    """
    mock_subprocess_run.return_value = MagicMock(stdout="+0000\n")
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    check.log = MagicMock()
    check.check(None)

    narrowed_closed = mock_collect_data.call_args[0][0]
    assert narrowed_closed == _boundary_closed[1:]


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_get_previous_iteration_log_cursor_when_cusror_is_none(utc_timestamp_minus_hours, instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    last_record_time, last_record_milli_sec, last_completed_closed, last_completed_open = (
        check.get_previous_iteration_log_cursor(None)
    )

    assert last_record_time == "20230401000000"
    assert last_record_milli_sec is None
    assert last_completed_closed == []
    assert last_completed_open == []


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_get_previous_iteration_log_cursor_when_cusror_is_not_none(utc_timestamp_minus_hours, instance):
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    previous_cursor = {
        "record_time": "20230401000000",
        "record_milli_sec": " + 430 msec",
        "last_completed_closed": ["20230401000000.20230401000015"],
        "last_completed_open": ["20230401000015.not_terminated"],
    }
    last_record_time, last_record_milli_sec, last_completed_closed, last_completed_open = (
        check.get_previous_iteration_log_cursor(previous_cursor)
    )

    assert last_record_time == "20230401000000"
    assert last_record_milli_sec == " + 430 msec"
    assert last_completed_closed == ["20230401000000.20230401000015"]
    assert last_completed_open == ["20230401000015.not_terminated"]


@pytest.mark.unit
@patch('datadog_checks.mac_audit_logs.check.subprocess.Popen')
def test_fetch_audit_logs(mock_popen, instance):
    """Multiple file paths are joined into a single auditreduce command."""
    logs = (
        "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 244 msec\" > /></record>\n<record time=\"Thu Jun  5 "
        "13:51:39 2025\" msec=\" + 154 msec\" > /></record>"
    )
    log_file_entries = logs.split("\n")
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    mock_auditreduce_stdout = MagicMock()
    mock_auditreduce_process = MagicMock(stdout=mock_auditreduce_stdout)
    mock_praudit_process = MagicMock(communicate=MagicMock(return_value=(logs, "")))

    mock_popen.side_effect = [mock_auditreduce_process, mock_praudit_process]

    file_paths = [
        "/var/audit/20250605082138.20250605082142",
        "/var/audit/20250605082142.20250605082150",
    ]
    time_filter_arg = "20250605132138"
    output, error = check.fetch_audit_logs(file_paths, time_filter_arg)

    mock_popen.assert_any_call(
        ["sudo", "auditreduce", "-a", time_filter_arg, file_paths[0], file_paths[1]],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "TZ": "UTC"},
    )
    mock_popen.assert_any_call(
        ["sudo", "praudit", "-xsl"],
        stdin=mock_auditreduce_stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    mock_praudit_process.communicate.assert_called_once()

    log_entries = output.split("\n")
    assert output == logs
    assert error == ""
    assert len(log_entries) == len(log_file_entries)


@pytest.mark.unit
@patch('datadog_checks.mac_audit_logs.check.subprocess.Popen')
def test_fetch_audit_logs_single_file(mock_popen, instance):
    """A single-element list produces the correct auditreduce command."""
    logs = "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 244 msec\" > /></record>"
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    mock_auditreduce_stdout = MagicMock()
    mock_auditreduce_process = MagicMock(stdout=mock_auditreduce_stdout)
    mock_praudit_process = MagicMock(communicate=MagicMock(return_value=(logs, "")))

    mock_popen.side_effect = [mock_auditreduce_process, mock_praudit_process]

    file_path = "/var/audit/20250605082138.20250605082142"
    time_filter_arg = "20250605132138"
    output, error = check.fetch_audit_logs([file_path], time_filter_arg)

    mock_popen.assert_any_call(
        ["sudo", "auditreduce", "-a", time_filter_arg, file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "TZ": "UTC"},
    )
    assert mock_popen.call_count == 2
    mock_praudit_process.communicate.assert_called_once()
    assert output == logs
    assert error == ""


def _make_closed(start: str, end: str) -> tuple[datetime, datetime, str]:
    return (
        utils.time_string_to_datetime_utc(start),
        utils.time_string_to_datetime_utc(end),
        f"{start}.{end}",
    )


THREE_CLOSED_FILES = [
    _make_closed("20230401000000", "20230401010000"),
    _make_closed("20230401010000", "20230401020000"),
    _make_closed("20230401020000", "20230401030000"),
]


def _path(check: MacAuditLogsCheck, file_name: str) -> str:
    return os.path.join(check.audit_logs_dir_path, file_name)


def _make_check_for_collection(instance: dict) -> MacAuditLogsCheck:
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    check.fetch_audit_logs = MagicMock(return_value=(b"<record/>", b""))
    check.process_and_ingest_log_entries = MagicMock()
    return check


@pytest.mark.unit
@pytest.mark.parametrize(
    "last_completed_closed,last_completed_open,last_record_time,expected_indices",
    [
        pytest.param([], [], "20230401000000", [0, 1, 2], id="batches_all_existing"),
        pytest.param([THREE_CLOSED_FILES[0][2]], [], "20230401010000", [1, 2], id="skips_already_processed"),
        pytest.param([], [], "20230401000000", [], id="no_valid_files"),
        pytest.param([], ["20230401000000.not_terminated"], "20230401010000", [1, 2], id="skips_rotated_open"),
        pytest.param([], [], "20230401000030", [0, 1, 2], id="always_uses_last_record_time"),
    ],
)
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_collect_data_from_files(
    mock_utc, last_completed_closed, last_completed_open, last_record_time, expected_indices, instance
):
    """Files surviving the skip checks are batched into one auditreduce call with
    the cursor's last-record timestamp as the filter."""
    check = _make_check_for_collection(instance)
    exists_return = expected_indices != []

    with patch("os.path.exists", return_value=exists_return):
        check.collect_data_from_files(
            THREE_CLOSED_FILES, [], last_completed_closed, last_completed_open, last_record_time, None, "+0000"
        )

    if not expected_indices:
        check.fetch_audit_logs.assert_not_called()
        return

    expected_names = [THREE_CLOSED_FILES[i][2] for i in expected_indices]
    expected_paths = [_path(check, name) for name in expected_names]
    check.fetch_audit_logs.assert_called_once_with(expected_paths, last_record_time)
    forwarded_completed_closed = check.process_and_ingest_log_entries.call_args[0][1]
    assert forwarded_completed_closed == expected_names


@pytest.mark.unit
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401000000")
def test_collect_data_from_files_excludes_missing_files(mock_utc, instance):
    """Files that no longer exist on disk are excluded from the auditreduce batch."""
    check = _make_check_for_collection(instance)
    missing_file = _path(check, THREE_CLOSED_FILES[1][2])

    with patch("os.path.exists", side_effect=lambda p: p != missing_file):
        check.collect_data_from_files(THREE_CLOSED_FILES, [], [], [], "20230401000000", None, "+0000")

    expected_paths = [_path(check, THREE_CLOSED_FILES[0][2]), _path(check, THREE_CLOSED_FILES[2][2])]
    check.fetch_audit_logs.assert_called_once_with(expected_paths, "20230401000000")


@pytest.mark.unit
@patch("os.path.isdir", return_value=True)
@patch("os.path.isfile", return_value=True)
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401030000")
@patch(
    "os.listdir",
    return_value=[
        "20230401000000.crash_recovery",
        "20230401040000.crash_recovery",
    ],
)
def test_collect_relevant_files_drops_crash_recovery_before_cutoff(
    _mock_listdir, _mock_get_utc, _mock_isfile, _mock_isdir, instance
):
    """Crash-recovery files whose start time is before the look-back cutoff are dropped;
    only those at or after the cutoff carry through as still-open candidates."""
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    closed, still_open = check.collect_relevant_files("20230401030000")
    assert closed == []
    assert still_open == [
        (utils.time_string_to_datetime_utc("20230401040000"), "20230401040000.crash_recovery"),
    ]


@pytest.mark.unit
@patch("os.path.isdir", return_value=True)
@patch("os.path.isfile", return_value=True)
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20230401030000")
@patch(
    "os.listdir",
    return_value=[
        "20230401000000.20230401010000",
        "20230401010000.20230401020000",
        "20230401030000.20230401040000",
    ],
)
def test_collect_relevant_files_excludes_out_of_window(
    _mock_listdir, _mock_get_utc, _mock_isfile, _mock_isdir, instance
):
    """Closed files whose end time is before the look-back cutoff are excluded."""
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    closed, still_open = check.collect_relevant_files("20230401030000")
    assert closed == [
        (
            utils.time_string_to_datetime_utc("20230401030000"),
            utils.time_string_to_datetime_utc("20230401040000"),
            "20230401030000.20230401040000",
        ),
    ]
    assert still_open == []


@pytest.mark.unit
@patch.object(MacAuditLogsCheck, 'send_log')
def test_process_and_ingest_log_entries_skipping_logs_milli_seconds(mock_send_log, instance):
    logs = (
        "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 244 msec\" > /></record>\n<record time=\"Thu Jun  5 "
        "13:51:38 2025\" msec=\" + 278 msec\" > /></record>\n<record time=\"Thu Jun  5 13:51:42 2025\" "
        "msec=\" + 124 msec\" > /></record>"
    )
    log_entries = logs.split("\n")
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    check.process_and_ingest_log_entries(log_entries, ["20250605082138.20250605082142"], [], "+0000", " + 278 msec")
    assert mock_send_log.call_count == 1


LOG_TEMPLATE_RECORDS = (
    "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 244 msec\" > /></record>\n"
    "<record time=\"Thu Jun  5 13:51:39 2025\" msec=\" + 154 msec\" > /></record>"
)
DEFAULT_BATCH_CLOSED = ["20250605082138.20250605082142"]


def _ingest(check: MacAuditLogsCheck, log_entries: list[str], resume_msec: str | None = None) -> None:
    check.process_and_ingest_log_entries(log_entries, DEFAULT_BATCH_CLOSED, [], "+0000", resume_msec)


# ---------------------------------------------------------------------------
# Deduplication across emissions
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch.object(MacAuditLogsCheck, "send_log")
def test_each_unique_record_is_emitted_at_most_once_per_cycle(mock_send_log, instance):
    """Within one cycle, every distinct record turns into at most one log entry."""
    logs = (
        "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 100 msec\" > /></record>\n"
        "<record time=\"Thu Jun  5 13:51:39 2025\" msec=\" + 200 msec\" > /></record>\n"
        "<record time=\"Thu Jun  5 13:51:40 2025\" msec=\" + 300 msec\" > /></record>"
    )
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    _ingest(check, logs.split("\n"))

    messages = [call.args[0]["message"] for call in mock_send_log.call_args_list]
    assert len(messages) == len(set(messages)) == 3


@pytest.mark.unit
@patch.object(MacAuditLogsCheck, "send_log")
def test_records_after_the_resume_point_are_emitted(mock_send_log, instance):
    """After the resume cursor's msec is matched, every subsequent record is emitted."""
    logs = (
        "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 100 msec\" > /></record>\n"
        "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 200 msec\" > /></record>\n"
        "<record time=\"Thu Jun  5 13:51:39 2025\" msec=\" + 300 msec\" > /></record>\n"
        "<record time=\"Thu Jun  5 13:51:40 2025\" msec=\" + 400 msec\" > /></record>"
    )
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    _ingest(check, logs.split("\n"), resume_msec=" + 200 msec")

    emitted_msecs = [
        msec
        for call in mock_send_log.call_args_list
        for msec in [" + 100 msec", " + 200 msec", " + 300 msec", " + 400 msec"]
        if msec in call.args[0]["message"]
    ]
    assert emitted_msecs == [" + 300 msec", " + 400 msec"]


# ---------------------------------------------------------------------------
# Cursor monotonicity
# ---------------------------------------------------------------------------


@pytest.mark.unit
@patch.object(MacAuditLogsCheck, "send_log")
@patch("os.path.exists", return_value=True)
@patch("datadog_checks.mac_audit_logs.utils.get_utc_timestamp_minus_hours", return_value="20250605000000")
def test_clean_resume_at_same_second_emits_only_new_records(_mock_utc, _mock_exists, mock_send_log, instance):
    """After a cleanly-completed cycle (`record_milli_sec=None`) the next cycle calls auditreduce
    with the cursor's `record_time` and must emit every record returned, including any that share
    the cursor's UTC second but come from a newly-rotated file. No record is dropped, no record is
    duplicated, because already-completed files are excluded before the batch."""
    completed_file = "20250605135137.20250605135138"
    new_file = "20250605135138.not_terminated"

    next_batch_logs = (
        b"<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 950 msec\" > /></record>\n"
        b"<record time=\"Thu Jun  5 13:51:39 2025\" msec=\" + 010 msec\" > /></record>"
    )
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])
    check.fetch_audit_logs = MagicMock(return_value=(next_batch_logs, b""))

    closed: list[tuple[datetime, datetime, str]] = []
    still_open = [(utils.time_string_to_datetime_utc("20250605135138"), new_file)]

    check.collect_data_from_files(
        closed,
        still_open,
        [completed_file],
        [],
        "20250605135138",
        None,
        "+0000",
    )

    check.fetch_audit_logs.assert_called_once()
    forwarded_paths, time_filter = check.fetch_audit_logs.call_args.args
    assert forwarded_paths == [_path(check, new_file)]
    assert time_filter == "20250605135138"

    emitted_msecs = [call.args[0]["message"] for call in mock_send_log.call_args_list]
    assert len(emitted_msecs) == 2
    assert " + 950 msec" in emitted_msecs[0]
    assert " + 010 msec" in emitted_msecs[1]


@pytest.mark.unit
@patch.object(MacAuditLogsCheck, "send_log")
def test_cursor_record_time_never_moves_backwards(mock_send_log, instance):
    """Successive cursors emitted within one cycle have monotonically non-decreasing record_time."""
    logs = (
        "<record time=\"Thu Jun  5 13:51:38 2025\" msec=\" + 100 msec\" > /></record>\n"
        "<record time=\"Thu Jun  5 13:51:39 2025\" msec=\" + 200 msec\" > /></record>\n"
        "<record time=\"Thu Jun  5 13:51:40 2025\" msec=\" + 300 msec\" > /></record>"
    )
    check = MacAuditLogsCheck("mac_audit_logs", {}, [instance])

    _ingest(check, logs.split("\n"))

    record_times = [call.kwargs["cursor"]["record_time"] for call in mock_send_log.call_args_list]
    assert record_times == sorted(record_times)
