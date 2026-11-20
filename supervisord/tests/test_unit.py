# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import socket
import xmlrpc.client as xmlrpclib

import mock
import pytest
from mock import patch

from datadog_checks.base.checks.base import ServiceCheck
from datadog_checks.supervisord.supervisord import FORMAT_TIME, SupervisordCheck

from .test_supervisord_unit import mock_server

pytestmark = pytest.mark.unit


def protocol_error_server(errcode):
    def factory(url, transport=None):
        server = mock.MagicMock()
        server.supervisor.getAllProcessInfo.side_effect = xmlrpclib.ProtocolError(url, errcode, "error", {})
        return server

    return factory


def test_user_key_logs_deprecation_warning_for_username(check):
    instance = {"name": "server1", "host": "localhost", "port": 9001, "user": "someone"}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=mock_server):
        check.check(instance)
    assert any("username" in w for w in check.get_warnings())


def test_pass_key_logs_deprecation_warning_for_password(check):
    instance = {"name": "server1", "host": "localhost", "port": 9001, "pass": "secret"}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=mock_server):
        check.check(instance)
    assert any("password" in w for w in check.get_warnings())


def socket_error_server(url, transport=None):
    server = mock.MagicMock()
    server.supervisor.getAllProcessInfo.side_effect = socket.error()
    return server


def test_socket_error_without_socket_key_reports_inet_message(check):
    instance = {"name": "server1", "host": "badhost", "port": 9009}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=socket_error_server):
        with pytest.raises(Exception, match="XML-RPC"):
            check.check(instance)


def test_socket_error_with_socket_key_reports_socket_file_message(check):
    instance = {"name": "server1", "socket": "unix:///tmp/nonexistent.sock"}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=socket_error_server):
        with pytest.raises(Exception, match="socket file"):
            check.check(instance)


def test_check_raises_when_server_name_is_only_whitespace(check):
    with pytest.raises(Exception, match="Supervisor server name not specified in yaml configuration."):
        check.check({"name": "   "})


@pytest.mark.parametrize("errcode", [400, 402])
def test_protocol_error_other_than_401_uses_generic_message(check, errcode):
    instance = {"name": "server1", "host": "localhost", "port": 9001}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=protocol_error_server(errcode)):
        with pytest.raises(Exception) as exc_info:
            check.check(instance)
    assert str(exc_info.value) == "An error occurred while connecting to server1: {} error".format(errcode)


@pytest.mark.parametrize(
    "field",
    ["proc_regex", "proc_regex_exclude", "proc_names", "proc_names_exclude"],
)
def test_invalid_filter_field_type_raises_with_percent_formatted_message(check, field):
    instance = {"name": "server1", "host": "localhost", "port": 9001, field: "not-a-list"}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=mock_server):
        with pytest.raises(Exception) as exc_info:
            check.check(instance)
    assert str(exc_info.value) == "'{}' should be a list of strings. e.g. {}".format(field, ["not-a-list"])


def test_status_mapping_override_invalid_value_raises_with_percent_formatted_message(check):
    instance = {
        "name": "server1",
        "host": "localhost",
        "port": 9001,
        "status_mapping_override": {"STOPPED": "invalid_status"},
    }
    with patch.object(xmlrpclib, "ServerProxy", side_effect=mock_server):
        with pytest.raises(Exception) as exc_info:
            check.check(instance)
    assert str(exc_info.value) == "'status_mapping_override' should be a status mapping e.g. STOPPED => invalid_status"


def test_process_filtering_continues_past_non_matching_names(aggregator, check):
    instance = {"name": "server1", "host": "localhost", "port": 9001, "proc_names": ["python"]}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=mock_server):
        check.check(instance)

    aggregator.assert_metric(
        "supervisord.process.count", value=1, tags=["supervisord_server:server1", "status:unknown"]
    )
    aggregator.assert_metric("supervisord.process.count", value=0, tags=["supervisord_server:server1", "status:up"])
    aggregator.assert_metric("supervisord.process.count", value=0, tags=["supervisord_server:server1", "status:down"])


def test_regex_exclude_alone_excludes_process(aggregator, check):
    instance = {"name": "server1", "host": "localhost", "port": 9001, "proc_regex_exclude": ["^my.*$"]}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=mock_server):
        check.check(instance)

    aggregator.assert_metric("supervisord.process.count", value=0, tags=["supervisord_server:server1", "status:up"])


def test_service_check_message_present_for_non_ok_status(aggregator, check):
    instance = {"name": "server1", "host": "localhost", "port": 9001}
    with patch.object(xmlrpclib, "ServerProxy", side_effect=mock_server):
        check.check(instance)

    aggregator.assert_service_check(
        "supervisord.process.status",
        status=ServiceCheck.CRITICAL,
        tags=["supervisord_server:server1", "supervisord_process:java"],
        message="Process name: java",
    )


def test_connect_requires_both_user_and_password_for_auth(check):
    captured_urls = []

    def fake_server_proxy(url, transport=None):
        captured_urls.append(url)
        return mock.MagicMock()

    with patch.object(xmlrpclib, "ServerProxy", side_effect=fake_server_proxy):
        SupervisordCheck._connect({"user": "someone", "host": "localhost", "port": 9001})

    assert captured_urls == ["http://localhost:9001/RPC2"]


def test_connect_falls_back_to_username_and_password_keys(check):
    captured_urls = []

    def fake_server_proxy(url, transport=None):
        captured_urls.append(url)
        return mock.MagicMock()

    with patch.object(xmlrpclib, "ServerProxy", side_effect=fake_server_proxy):
        SupervisordCheck._connect({"username": "realuser", "password": "realpass", "host": "localhost", "port": 9001})

    assert captured_urls == ["http://realuser:realpass@localhost:9001/RPC2"]


def test_extract_uptime_active_state_subtracts_start_from_now(check):
    proc = {"start": 10, "now": 25, "statename": "RUNNING"}
    assert check._extract_uptime(proc) == 15


def test_extract_uptime_inactive_state_returns_zero(check):
    proc = {"start": 10, "now": 25, "statename": "STOPPED"}
    assert check._extract_uptime(proc) == 0


def build_message_process(stop):
    return {
        "now": 1414815513,
        "group": "mysql",
        "description": "desc",
        "stderr_logfile": "/log",
        "stop": stop,
        "statename": "RUNNING",
        "start": 1414815388,
        "stdout_logfile": "/log",
        "logfile": "/log",
        "exitstatus": 0,
        "name": "mysql",
    }


def test_build_message_formats_positive_stop_time(check):
    message = check._build_message(build_message_process(100))
    assert "Stop time: {}".format(FORMAT_TIME(100)) in message


def test_build_message_formats_negative_stop_time(check):
    message = check._build_message(build_message_process(-50))
    assert "Stop time: {}".format(FORMAT_TIME(-50)) in message


def test_build_message_omits_stop_time_when_zero(check):
    message = check._build_message(build_message_process(0))
    assert "Stop time: \nExit Status:" in message
