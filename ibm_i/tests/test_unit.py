# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import io
import itertools
import os
import sys
import types
from datetime import datetime, timedelta
from typing import Any, Dict  # noqa: F401

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.ibm_i import IbmICheck
from datadog_checks.ibm_i import queries as ibm_i_queries
from datadog_checks.ibm_i.check import SystemInfo

try:
    import pyodbc  # noqa: F401
except ImportError:
    # pyodbc's native driver isn't available in this environment. query_script only
    # needs the module to exist so it can be imported and have `.connect` mocked.
    stub_pyodbc = types.ModuleType("pyodbc")
    stub_pyodbc.connect = lambda *args, **kwargs: None
    sys.modules["pyodbc"] = stub_pyodbc

from datadog_checks.ibm_i import query_script  # noqa: E402

pytestmark = pytest.mark.unit


class FlushTrackingStream(io.StringIO):
    """A StringIO that records how many times flush() was explicitly called."""

    def __init__(self):
        super().__init__()
        self.flush_count = 0

    def flush(self):
        self.flush_count += 1
        super().flush()


# --- check() -----------------------------------------------------------------


def test_check_no_query_manager_uses_config_hostname(aggregator, instance):
    instance = {**instance, "hostname": "configured-host"}
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck.fetch_system_info", return_value=None):
        check.check(instance)
    assert check._query_manager is None
    check.log.warning.assert_called_once()
    aggregator.assert_service_check("ibm_i.can_connect", status=AgentCheck.CRITICAL, hostname="configured-host")


def test_check_query_manager_execute_error_uses_config_hostname(aggregator, instance):
    instance = {**instance, "hostname": "configured-host"}
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    check._query_manager = mock.MagicMock(hostname="other-host")
    check._query_manager.execute.side_effect = Exception("boom")

    with mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as delete_conn:
        check.check(instance)

    delete_conn.assert_called_once()
    aggregator.assert_service_check("ibm_i.can_connect", status=AgentCheck.CRITICAL, hostname="configured-host")


def test_cancel(instance):
    # Baseline coverage for cancel(); needed since this isolated file gets no credit
    # from test_ibm_i.py's coverage of the same line.
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as m:
        check.cancel()
    m.assert_called_once()


# --- connection_string ---------------------------------------------------------


def test_connection_string_no_fields(instance):
    instance = {**instance, "driver": "driver"}
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    assert check.connection_string == "Driver={driver};"


def test_connection_string_all_fields(instance):
    # Baseline coverage for the connection_string property's field concatenation.
    instance = {
        **instance,
        "driver": "driver",
        "system": "system",
        "username": "username",
        "password": "password",
    }
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    assert check.connection_string == "Driver={driver};System=system;UID=username;PWD=password;"


def test_connection_string_defined_and_cached(instance):
    # Baseline coverage for the connection_string property's caching behavior.
    instance = {
        **instance,
        "connection_string": "constring",
        "driver": "driver",
        "system": "system",
        "username": "username",
        "password": "password",
    }
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    assert check.connection_string == "constring"
    check._connection_string = "modified"
    assert check.connection_string == "modified"


# --- _create_connection_subprocess / connection_subprocess ---------------------


def test_create_connection_subprocess_sets_text_mode_and_nonblocking_flags(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    fake_process = mock.MagicMock()
    # A flag value that already has O_NONBLOCK set, so ADD/SUB/MUL/DIV/etc. mutations
    # on the `fl | os.O_NONBLOCK` expressions all produce a value different from `fl`.
    with (
        mock.patch("subprocess.Popen", return_value=fake_process) as popen,
        mock.patch("fcntl.fcntl", return_value=os.O_NONBLOCK + 1) as fcntl_fcntl,
    ):
        check._create_connection_subprocess()

    assert popen.call_args.kwargs["text"] is True

    setfl_calls = [c for c in fcntl_fcntl.call_args_list if len(c.args) == 3]
    set_flags = {c.args[2] for c in setfl_calls}
    assert set_flags == {os.O_NONBLOCK + 1}


def test_create_connection_subprocess_writes_connection_string_and_flushes(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    fake_process = mock.MagicMock()
    with (
        mock.patch("subprocess.Popen", return_value=fake_process),
        mock.patch("fcntl.fcntl", return_value=os.O_NONBLOCK + 1),
    ):
        check._create_connection_subprocess()

    fake_process.stdin.flush.assert_called_once()


def test_create_connection_subprocess_broken_pipe_cleans_up(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    fake_process = mock.MagicMock()
    fake_process.stdin.flush.side_effect = BrokenPipeError("broken")
    with (
        mock.patch("subprocess.Popen", return_value=fake_process),
        mock.patch("fcntl.fcntl", return_value=os.O_NONBLOCK + 1),
        mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as delete_conn,
    ):
        check._create_connection_subprocess()

    delete_conn.assert_called_once()


def test_connection_subprocess_lazily_creates_once(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck._create_connection_subprocess") as create:
        _ = check.connection_subprocess
        check._subprocess = mock.MagicMock()
        _ = check.connection_subprocess
    create.assert_called_once()


# --- _delete_connection_subprocess ----------------------------------------------


def test_delete_connection_subprocess_kills_and_waits_until_exited(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    subprocess_mock = mock.MagicMock()
    check._subprocess = subprocess_mock
    # None, None, then a truthy (non-zero) return code once the process has exited.
    return_codes = iter([None, None, -9])
    type(subprocess_mock).returncode = mock.PropertyMock(side_effect=lambda: next(return_codes))

    check._delete_connection_subprocess("some reason")

    assert subprocess_mock.kill.call_count == 2
    assert subprocess_mock.wait.call_count == 2
    assert check._subprocess is None


def test_delete_connection_subprocess_noop_when_none(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    check._subprocess = None
    check._delete_connection_subprocess("some reason")
    assert check._subprocess is None


# --- execute_query ---------------------------------------------------------------


def _make_check_with_subprocess(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    check._subprocess = mock.MagicMock()
    check._subprocess.stderr.read.return_value = ""
    return check


def test_execute_query_writes_query_text_and_flushes(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = itertools.chain(["ENDOFQUERY\n"], itertools.repeat(""))

    with mock.patch("datadog_checks.ibm_i.check.time.sleep"):
        list(check.execute_query({"text": "SELECT 1", "timeout": 2}))

    check._subprocess.stdin.flush.assert_called_once()


def test_execute_query_broken_pipe_on_write_returns_early(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdin.flush.side_effect = BrokenPipeError("broken")

    with mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as delete_conn:
        result = list(check.execute_query({"text": "SELECT 1", "timeout": 2}))

    assert result == []
    delete_conn.assert_called_once()


def test_execute_query_skips_wait_loop_when_already_past_boundary(instance):
    check = _make_check_with_subprocess(instance)
    start = datetime(2024, 1, 1, 0, 0, 0)
    with (
        mock.patch("datadog_checks.ibm_i.check.datetime") as dt_mock,
        mock.patch("datadog_checks.ibm_i.check.time.sleep") as sleep_mock,
    ):
        dt_mock.now.side_effect = itertools.chain([start], itertools.repeat(start + timedelta(seconds=1000)))
        with pytest.raises(Exception, match="Timed out after -1 seconds"):
            list(check.execute_query({"text": "SELECT 1", "timeout": -1}))

    sleep_mock.assert_not_called()


def test_execute_query_enters_wait_loop_exactly_at_timeout_boundary(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = ["ENDOFQUERY\n"]
    start = datetime(2024, 1, 1, 0, 0, 0)
    with (
        mock.patch("datadog_checks.ibm_i.check.datetime") as dt_mock,
        mock.patch("datadog_checks.ibm_i.check.time.sleep") as sleep_mock,
    ):
        dt_mock.now.side_effect = [start, start + timedelta(seconds=2)]
        result = list(check.execute_query({"text": "SELECT 1", "timeout": 2}))

    assert result == []
    sleep_mock.assert_called_once_with(0.2)


def test_execute_query_parses_lines_and_skips_blank_lines(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = ['{"a": 1}\n', "\n", '{"a": 2}\n', "ENDOFQUERY\n"]

    with mock.patch("datadog_checks.ibm_i.check.time.sleep") as sleep_mock:
        result = list(check.execute_query({"text": "SELECT 1", "timeout": 5}))

    assert result == [{"a": 1}, {"a": 2}]
    sleep_mock.assert_called_once_with(0.2)


def test_execute_query_stops_immediately_at_exact_marker(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = itertools.chain(
        ['"AAA"\n', "ENDOFQUERY\n", '"BBB"\n'], itertools.repeat("")
    )

    with mock.patch("datadog_checks.ibm_i.check.time.sleep"):
        result = list(check.execute_query({"text": "SELECT 1", "timeout": 2}))

    assert result == ["AAA"]


def test_execute_query_invalid_json_deletes_subprocess_and_raises(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = ["not-json\n"]

    with (
        mock.patch("datadog_checks.ibm_i.check.time.sleep"),
        mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as delete_conn,
    ):
        with pytest.raises(Exception):
            list(check.execute_query({"text": "SELECT 1", "timeout": 5}))

    delete_conn.assert_called_once()


def test_execute_query_typeerror_on_readline_retries(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = [TypeError("would block"), "ENDOFQUERY\n"]

    with mock.patch("datadog_checks.ibm_i.check.time.sleep") as sleep_mock:
        result = list(check.execute_query({"text": "SELECT 1", "timeout": 5}))

    assert result == []
    assert sleep_mock.call_count == 2


def test_execute_query_broken_pipe_on_readline_returns_early(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = BrokenPipeError("broken")

    with (
        mock.patch("datadog_checks.ibm_i.check.time.sleep"),
        mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as delete_conn,
    ):
        result = list(check.execute_query({"text": "SELECT 1", "timeout": 5}))

    assert result == []
    delete_conn.assert_called_once()


def test_execute_query_typeerror_on_stderr_read_completes_cleanly(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = ["ENDOFQUERY\n"]
    check._subprocess.stderr.read.side_effect = TypeError("would block")

    with mock.patch("datadog_checks.ibm_i.check.time.sleep"):
        result = list(check.execute_query({"text": "SELECT 1", "timeout": 5}))

    assert result == []


def test_execute_query_broken_pipe_on_stderr_read_returns_early(instance):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = ["ENDOFQUERY\n"]
    check._subprocess.stderr.read.side_effect = BrokenPipeError("broken")

    with (
        mock.patch("datadog_checks.ibm_i.check.time.sleep"),
        mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as delete_conn,
    ):
        result = list(check.execute_query({"text": "SELECT 1", "timeout": 5}))

    assert result == []
    delete_conn.assert_called_once()


@pytest.mark.parametrize("disconnect_on_error", [True, False])
def test_execute_query_stderr_error_raises_and_disconnects_conditionally(instance, disconnect_on_error):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = itertools.chain(["ENDOFQUERY\n"], itertools.repeat(""))
    check._subprocess.stderr.read.return_value = "boom"

    with (
        mock.patch("datadog_checks.ibm_i.check.time.sleep"),
        mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as delete_conn,
    ):
        with pytest.raises(Exception, match="boom"):
            list(check.execute_query({"text": "SELECT 1", "timeout": 5}, disconnect_on_error=disconnect_on_error))

    if disconnect_on_error:
        delete_conn.assert_called_once()
    else:
        delete_conn.assert_not_called()


@pytest.mark.parametrize("disconnect_on_error", [True, False])
def test_execute_query_timeout_raises_and_disconnects_conditionally(instance, disconnect_on_error):
    check = _make_check_with_subprocess(instance)
    check._subprocess.stdout.readline.side_effect = itertools.chain([], itertools.repeat(""))

    with (
        mock.patch("datadog_checks.ibm_i.IbmICheck._delete_connection_subprocess") as delete_conn,
    ):
        with pytest.raises(Exception, match="Timed out after -1 seconds"):
            list(check.execute_query({"text": "SELECT 1", "timeout": -1}, disconnect_on_error=disconnect_on_error))

    if disconnect_on_error:
        delete_conn.assert_called_once()
    else:
        delete_conn.assert_not_called()


# --- set_up_query_manager --------------------------------------------------------


def test_set_up_query_manager_error(instance):
    # Baseline coverage: no query manager gets created when system info can't be fetched.
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    with mock.patch("datadog_checks.ibm_i.IbmICheck.fetch_system_info", return_value=None):
        check.set_up_query_manager()
    assert check._query_manager is None


@pytest.mark.parametrize(
    "os_version, os_release, expected_query_names",
    [
        (6, 9, {"base_disk_usage_72"}),
        (7, 2, {"base_disk_usage_72"}),
        (7, 3, {"base_disk_usage_73", "disk_usage", "subsystem"}),
        (7, 4, {"base_disk_usage_73", "disk_usage", "subsystem"}),
        (8, 0, {"base_disk_usage_73", "disk_usage", "subsystem"}),
    ],
)
def test_set_up_query_manager_7_3_boundary(instance, os_version, os_release, expected_query_names):
    instance = {**instance, "queries": [{"name": "disk_usage"}, {"name": "subsystem"}]}
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        "datadog_checks.ibm_i.IbmICheck.fetch_system_info",
        return_value=SystemInfo("host", os_version, os_release),
    ):
        check.set_up_query_manager()

    query_names = {q.name for q in check._query_manager.queries}
    assert query_names == expected_query_names


def test_set_up_query_manager_hostname_override(instance):
    # Baseline coverage for the hostname override branch (check.py:236-237).
    instance = {**instance, "hostname": "overridden-hostname"}
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck.fetch_system_info", return_value=SystemInfo("host", 7, 4)):
        check.set_up_query_manager()
    assert check._query_manager.hostname == "overridden-hostname"


def test_set_up_query_manager_unknown_query_raises(instance):
    # Baseline coverage for the ConfigurationError branch (check.py:229-230).
    from datadog_checks.base import ConfigurationError

    instance = {**instance, "queries": [{"name": "not_a_real_query"}]}
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck.fetch_system_info", return_value=SystemInfo("host", 7, 4)):
        with pytest.raises(ConfigurationError):
            check.set_up_query_manager()


# --- fetch_system_info / system_info_query ---------------------------------------


def test_fetch_system_info_wraps_and_logs_errors(instance):
    # Baseline coverage for fetch_system_info's outer try/except (check.py:248-254).
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck.execute_query", side_effect=Exception("boom")):
        system_info = check.fetch_system_info()
    assert system_info is None
    check.log.error.assert_called_once()


def test_system_info_query_empty_results(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck.execute_query", return_value=[]):
        system_info = check.system_info_query()
    assert system_info is None
    check.log.error.assert_called_once()


def test_system_info_query_too_many_results(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    rows = [("host", "7", "3"), ("host2", "7", "3")]
    with mock.patch("datadog_checks.ibm_i.IbmICheck.execute_query", return_value=rows):
        system_info = check.system_info_query()
    assert system_info is None
    check.log.error.assert_called_once()


def test_system_info_query_too_few_columns(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck.execute_query", return_value=[("host", "7")]):
        system_info = check.system_info_query()
    assert system_info is None
    check.log.error.assert_called_once()


def test_system_info_query_too_many_columns(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch("datadog_checks.ibm_i.IbmICheck.execute_query", return_value=[("host", "7", "3", "extra")]):
        system_info = check.system_info_query()
    assert system_info is None
    check.log.error.assert_called_once()


def test_system_info_query_invalid_os_version(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        "datadog_checks.ibm_i.IbmICheck.execute_query",
        return_value=[("the-host", "invalid-version", "the-release")],
    ):
        system_info = check.system_info_query()
    assert system_info is None
    check.log.error.assert_called_once_with("Expected integer for OS version, got %s", "invalid-version")


def test_system_info_query_invalid_os_release(instance):
    check = IbmICheck("ibm_i", {}, [instance])
    check.log = mock.MagicMock()
    check.load_configuration_models()
    with mock.patch(
        "datadog_checks.ibm_i.IbmICheck.execute_query",
        return_value=[("the-host", "7", "invalid-release")],
    ):
        system_info = check.system_info_query()
    assert system_info is None
    check.log.error.assert_called_once_with("Expected integer for OS release, got %s", "invalid-release")


# --- queries.py ------------------------------------------------------------------


@pytest.mark.parametrize(
    "selected_message_queues, expect_filter",
    [
        ([], False),
        (["QSYSOPR"], True),
    ],
)
def test_get_message_queue_info_filter(instance, selected_message_queues, expect_filter):
    instance = {**instance, "message_queue_info": {"selected_message_queues": selected_message_queues}}
    check = IbmICheck("ibm_i", {}, [instance])
    check.load_configuration_models()
    query = ibm_i_queries.query_map(check.config)["message_queue_info"]

    if expect_filter:
        assert "WHERE MESSAGE_QUEUE_NAME IN ('QSYSOPR')" in query["query"]["text"]
    else:
        assert "WHERE" not in query["query"]["text"]


# --- query_script.py ---------------------------------------------------------------


def test_query_script_connects_and_executes_query_lines():
    connection = mock.MagicMock()
    connection.execute.return_value.fetchall.return_value = []
    fake_out = FlushTrackingStream()
    fake_err = FlushTrackingStream()
    with (
        mock.patch.object(query_script.sys, "stdin", new=io.StringIO("connstring\nSELECT 1\n")),
        mock.patch.object(query_script.sys, "stdout", new=fake_out),
        mock.patch.object(query_script.sys, "stderr", new=fake_err),
        mock.patch("datadog_checks.ibm_i.query_script.pyodbc.connect", return_value=connection) as connect_mock,
    ):
        query_script.query()

    connect_mock.assert_called_once_with("connstring")
    connection.execute.assert_called_once_with("SELECT 1")


def test_query_script_connect_failure_prints_error_and_marker():
    fake_out = FlushTrackingStream()
    fake_err = FlushTrackingStream()
    with (
        mock.patch.object(query_script.sys, "stdin", new=io.StringIO("badconn\n")),
        mock.patch.object(query_script.sys, "stdout", new=fake_out),
        mock.patch.object(query_script.sys, "stderr", new=fake_err),
        mock.patch("datadog_checks.ibm_i.query_script.pyodbc.connect", side_effect=Exception("boom")),
    ):
        query_script.query()

    assert "boom" in fake_err.getvalue()
    assert fake_out.getvalue().strip() == "ENDOFQUERY"
    assert fake_err.flush_count >= 1
    assert fake_out.flush_count >= 1


def test_query_script_prints_rows_then_marker():
    from datadog_checks.base.utils.serialization import impl as json_impl

    connection = mock.MagicMock()
    connection.execute.return_value.fetchall.return_value = [("x", None), ("y", "z")]
    fake_out = FlushTrackingStream()
    fake_err = FlushTrackingStream()
    with (
        mock.patch.object(query_script.sys, "stdin", new=io.StringIO("connstring\nSELECT 1\n")),
        mock.patch.object(query_script.sys, "stdout", new=fake_out),
        mock.patch.object(query_script.sys, "stderr", new=fake_err),
        mock.patch("datadog_checks.ibm_i.query_script.pyodbc.connect", return_value=connection),
    ):
        query_script.query()

    lines = [line for line in fake_out.getvalue().splitlines() if line]
    if json_impl == "orjson":
        from datadog_checks.base.utils.serialization import json as agent_json

        expected_row_1 = agent_json.dumps(["x", None]).decode("utf-8")
        expected_row_2 = agent_json.dumps(["y", "z"]).decode("utf-8")
        assert lines == [expected_row_1, expected_row_2, "ENDOFQUERY"]
        assert fake_out.flush_count == 3
    else:
        assert lines == ["ENDOFQUERY"]
        assert fake_err.getvalue() != ""


def test_query_script_execution_error_prints_error_and_marker():
    connection = mock.MagicMock()
    connection.execute.side_effect = Exception("bad sql")
    fake_out = FlushTrackingStream()
    fake_err = FlushTrackingStream()
    with (
        mock.patch.object(query_script.sys, "stdin", new=io.StringIO("connstring\nSELECT bad\n")),
        mock.patch.object(query_script.sys, "stdout", new=fake_out),
        mock.patch.object(query_script.sys, "stderr", new=fake_err),
        mock.patch("datadog_checks.ibm_i.query_script.pyodbc.connect", return_value=connection),
    ):
        query_script.query()

    assert "bad sql" in fake_err.getvalue()
    assert fake_out.getvalue().strip() == "ENDOFQUERY"
    assert fake_err.flush_count >= 1
