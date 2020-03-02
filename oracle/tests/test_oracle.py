# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.oracle import Oracle

from .common import CHECK_NAME


def test__get_connection_instant_client(check):
    """
    Test the _get_connection method using the instant client
    """
    check.use_oracle_client = True
    con = mock.MagicMock()
    service_check = mock.MagicMock()
    check.service_check = service_check
    expected_tags = ['server:localhost:1521', 'optional:tag1']
    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle') as cx:
        cx.connect.return_value = con
        check.create_connection()
        assert check._connection == con
        cx.connect.assert_called_with('system/oracle@//localhost:1521/xe')
        service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.OK, tags=expected_tags)


def test__get_connection_jdbc(check):
    """
    Test the _get_connection method using the JDBC client
    """
    check.use_oracle_client = False
    con = mock.MagicMock()
    service_check = mock.MagicMock()
    check.service_check = service_check
    expected_tags = ['server:localhost:1521', 'optional:tag1']
    with mock.patch('datadog_checks.oracle.oracle.cx_Oracle') as cx:
        cx.DatabaseError = RuntimeError
        cx.clientversion.side_effect = cx.DatabaseError()
        with mock.patch('datadog_checks.oracle.oracle.jdb') as jdb:
            with mock.patch('datadog_checks.oracle.oracle.jpype') as jpype:
                jpype.isJVMStarted.return_value = False
                jdb.connect.return_value = con
                check.create_connection()
                assert check._connection == con
                jdb.connect.assert_called_with(
                    'oracle.jdbc.OracleDriver', 'jdbc:oracle:thin:@//localhost:1521/xe', ['system', 'oracle'], None
                )
                service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.OK, tags=expected_tags)


def test__get_connection_failure(check):
    """
    Test the right service check is sent upon _get_connection failures
    """
    expected_tags = ['server:localhost:1521', 'optional:tag1']
    service_check = mock.MagicMock()
    check.service_check = service_check
    with pytest.raises(Exception):
        check.create_connection()
    service_check.assert_called_with(check.SERVICE_CHECK_NAME, check.CRITICAL, tags=expected_tags)


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


def __test__check_only_custom_queries_set_false(check, instance):
    """
    Test the default metrics are called when only_custom queries is set to False
    """
    assert check._query_manager.queries != []
