# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from unittest.mock import MagicMock, patch

import pymysql
import pytest

from datadog_checks.mysql import MySql

from . import common

pytestmark = pytest.mark.unit


def test_connection_with_defaults_file():
    file_instance = {
        'host': 'localhost',
        'port': '123',
        'user': 'ddog',
        'defaults_file': '/foo/bar',
    }
    check = MySql(common.CHECK_NAME, {}, [file_instance])
    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': None,
        'read_default_file': '/foo/bar',
    }
    assert 'host' not in connection_args


def test_connection_with_sock():
    file_instance = {
        'host': 'localhost',
        'port': '123',
        'user': 'ddog',
        'pass': 'pwd',
        'sock': '/foo/bar',
    }
    check = MySql(common.CHECK_NAME, {}, [file_instance])
    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': None,
        'unix_socket': '/foo/bar',
        'user': 'ddog',
        'passwd': 'pwd',
        'port': 123,
    }


def test_connection_with_host():
    file_instance = {
        'host': 'localhost',
        'user': 'ddog',
        'pass': 'pwd',
    }
    check = MySql(common.CHECK_NAME, {}, [file_instance])
    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': None,
        'user': 'ddog',
        'passwd': 'pwd',
        'host': 'localhost',
    }


def test_connection_with_host_and_port():
    file_instance = {'host': 'localhost', 'user': 'ddog', 'pass': 'pwd', 'port': '123'}
    check = MySql(common.CHECK_NAME, {}, [file_instance])
    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': None,
        'user': 'ddog',
        'passwd': 'pwd',
        'host': 'localhost',
        'port': 123,
    }


def test_connection_with_charset(instance_basic):
    instance = copy.deepcopy(instance_basic)
    instance['charset'] = 'utf8mb4'
    check = MySql(common.CHECK_NAME, {}, [instance])

    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'host': common.HOST,
        'user': common.USER,
        'passwd': common.PASS,
        'port': common.PORT,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': None,
        'charset': 'utf8mb4',
    }


def _capture_warnings(check):
    """Return a list that accumulates warning messages logged by the check."""
    import logging

    captured = []

    class _WarnCapture(logging.Handler):
        def emit(self, record):
            if record.levelno == logging.WARNING:
                captured.append(record.getMessage())

    handler = _WarnCapture()
    check.log.logger.addHandler(handler)
    check.log.logger.setLevel(logging.WARNING)
    return captured, handler


def test_1045_warns_ssl_hint_when_no_ssl_configured(instance_basic):
    check = MySql(common.CHECK_NAME, {}, [instance_basic])
    captured, handler = _capture_warnings(check)
    try:
        with patch('datadog_checks.mysql.mysql.connect_with_session_variables') as mock_connect, \
             patch.object(check, 'service_check'):
            mock_connect.side_effect = pymysql.err.OperationalError(1045, "Access denied")
            with pytest.raises(pymysql.err.OperationalError):
                with check._connect():
                    pass
        assert any('ssl' in w.lower() for w in captured), f"Expected ssl warning, got: {captured}"
        assert any('1045' in w for w in captured), f"Expected 1045 in warning, got: {captured}"
    finally:
        check.log.logger.removeHandler(handler)


def test_1045_no_ssl_hint_when_ssl_already_configured(instance_basic):
    instance = copy.deepcopy(instance_basic)
    instance['ssl'] = {'check_hostname': False}
    check = MySql(common.CHECK_NAME, {}, [instance])
    captured, handler = _capture_warnings(check)
    try:
        with patch('datadog_checks.mysql.mysql.connect_with_session_variables') as mock_connect, \
             patch.object(check, 'service_check'):
            mock_connect.side_effect = pymysql.err.OperationalError(1045, "Access denied")
            with pytest.raises(pymysql.err.OperationalError):
                with check._connect():
                    pass
        ssl_warns = [w for w in captured if 'ssl' in w.lower() and '1045' in w]
        assert ssl_warns == [], f"Unexpected ssl/1045 warning when ssl configured: {ssl_warns}"
    finally:
        check.log.logger.removeHandler(handler)
