# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import cx_Oracle
import pytest

try:
    from contextlib import ExitStack
except ImportError:
    # TODO: Remove when
    from contextlib2 import ExitStack

import mock

from datadog_checks.oracle import Oracle

from .common import CHECK_NAME

SYS_DBA = cx_Oracle.SYSDBA


@pytest.mark.parametrize("as_sysdba", [True, False])
def test_get_connection_instant_client(check, dd_run_check, as_sysdba):
    """
    Test the _get_connection method using the instant client
    """
    check.use_oracle_client = True
    check._as_sysdba = as_sysdba
    con = mock.MagicMock()
    service_check = mock.MagicMock()
    check.service_check = service_check
    expected_tags = ['server:localhost:1521', 'optional:tag1']

    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle') as cx:
        cx.connect.return_value = con
        mode = cx.SYSDBA if as_sysdba else cx.DEFAULT_AUTH

        dd_run_check(check)
        assert check._cached_connection == con
        cx.connect.assert_called_with(user='system', password='oracle', dsn=check._get_dsn(), mode=mode)
        service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.OK, tags=expected_tags)


@pytest.mark.parametrize("as_sysdba", [True, False])
def test_get_connection_jdbc(check, dd_run_check, as_sysdba):
    """
    Test the _get_connection method using the JDBC client
    """
    check.use_oracle_client = False
    check._as_sysdba = as_sysdba
    con = mock.MagicMock()
    service_check = mock.MagicMock()
    check.service_check = service_check
    expected_tags = ['server:localhost:1521', 'optional:tag1']

    cx = mock.MagicMock(DatabaseError=RuntimeError)
    cx.clientversion.side_effect = cx.DatabaseError()

    jdb = mock.MagicMock()
    jdb.connect.return_value = con
    jpype = mock.MagicMock(isJVMStarted=lambda: False)

    mocks = [
        ('datadog_checks.oracle.oracle.cx_Oracle', cx),
        ('datadog_checks.oracle.oracle.jdb', jdb),
        ('datadog_checks.oracle.oracle.jpype', jpype),
        ('datadog_checks.oracle.oracle.JDBC_IMPORT_ERROR', None),
    ]
    with ExitStack() as stack:
        for mock_call in mocks:
            stack.enter_context(mock.patch(*mock_call))
        dd_run_check(check)
        assert check._cached_connection == con

    user = 'system' + (' AS SYSDBA' if as_sysdba else '')
    jdb.connect.assert_called_with(
        'oracle.jdbc.OracleDriver', 'jdbc:oracle:thin:@//localhost:1521/xe', [user, 'oracle'], None
    )
    service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.OK, tags=expected_tags)


def test__get_connection_failure(check, dd_run_check):
    """
    Test the right service check is sent upon _get_connection failures
    """
    expected_tags = ['server:localhost:1521', 'optional:tag1']
    service_check = mock.MagicMock()
    check.service_check = service_check
    dd_run_check(check)
    service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.CRITICAL, tags=expected_tags)
    assert check._cached_connection is None


def test__check_only_custom_queries(instance):
    """
    Test the default metrics are not called when only_custom queries set to true
    """
    instance['only_custom_queries'] = True

    check = Oracle(CHECK_NAME, {}, [instance])

    assert check._query_manager.queries == []


def test__check_only_custom_queries_not_set(instance):
    """
    Test the default metrics are called when only_custom queries is not set
    """
    instance['only_custom_queries'] = False

    check = Oracle(CHECK_NAME, {}, [instance])

    assert check._query_manager.queries != []


def __test__check_only_custom_queries_set_false(check):
    """
    Test the default metrics are called when only_custom queries is set to False
    """
    assert check._query_manager.queries != []
