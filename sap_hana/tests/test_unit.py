# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.sap_hana import SapHanaCheck
from datadog_checks.sap_hana.connection import HanaConnection

pytestmark = pytest.mark.unit


def error(*args, **kwargs):
    raise Exception('test')


def test_error_query(instance):
    check = SapHanaCheck('sap_hana', {}, [instance])
    check.log = mock.MagicMock()

    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.execute = error
    conn.cursor = lambda: cursor
    check._conn = conn

    check.check(None)
    check.log.error.assert_any_call('Error querying %s: %s', 'SYS.M_DATABASE', 'test')


def test_error_unknown(instance):
    def query_master_database():
        error()

    check = SapHanaCheck('sap_hana', {}, [instance])
    check.log = mock.MagicMock()

    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.execute = error
    conn.cursor = lambda: cursor
    check._conn = conn

    check.query_master_database = query_master_database

    check.check(None)
    check.log.error.assert_any_call('Unexpected error running `%s`: %s', 'query_master_database', 'test')


def test_custom_query_configuration(instance):
    def rows_generator():
        all_rows = [[['foo', 'bar'], ['foo', 'bar']]]

        def _get_rows(_):
            if not all_rows:
                return
            return all_rows.pop()

        return _get_rows

    check = SapHanaCheck('sap_hana', {}, [instance])
    log = mock.MagicMock()
    gauge = mock.MagicMock()
    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.fetchmany = rows_generator()
    conn.cursor.return_value = cursor
    check._conn = conn
    check.log = log
    check.gauge = gauge

    query = {}
    check._custom_queries = [query]

    # No query
    check.query_custom()
    log.error.assert_called_once_with('Custom query field `query` is required')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    # No columns
    query['query'] = 'foo'

    check.query_custom()
    log.error.assert_called_once_with('Custom query field `columns` is required')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    # Columns count incorrect
    query['columns'] = [{}]

    check.query_custom()
    log.error.assert_any_call('Custom query result expected %s column(s), got %s', 1, 2)
    assert log.error.call_count == 2
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    # No name
    column_1 = {'name': 'baz', 'type': 'tag'}
    column_2 = {'foo': 'bar'}
    columns = [column_1, column_2]
    query['columns'] = columns

    check.query_custom()
    log.error.assert_any_call('Column field `name` is required')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    # No type
    del column_2['foo']
    column_2['name'] = 'foo'

    check.query_custom()
    log.error.assert_any_call('Column field `type` is required for column `%s`', 'foo')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    # Unknown type
    column_2['type'] = 'unknown'

    check.query_custom()
    log.error.assert_any_call('Invalid submission method `%s` for metric column `%s`', 'unknown', 'foo')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    # Non-numeric value
    column_2['type'] = 'gauge'

    check.query_custom()
    log.error.assert_any_call('Non-numeric value `%s` for metric column `%s`', 'bar', 'foo')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    gauge.assert_not_called()


def test_tls_overwrite():
    """Tests that the connection class correctly overrides the `_open_socket_and_init_protocoll` method.
    The fact that there is a typo in the private method name makes it possible that this could change in the future.
    """
    tls_context = mock.MagicMock()
    socket = mock.MagicMock()
    conn = HanaConnection("localhost", 8000, 'foo', 'bar', tls_context=tls_context)
    with mock.patch('socket.create_connection', mock.MagicMock(return_value=socket)):
        socket.recv.return_value = b'12345678'
        tls_context.wrap_socket.return_value = socket
        with pytest.raises(Exception, match='Invalid message header received'):
            conn.connect()
        tls_context.wrap_socket.assert_called()


def test_no_tls_overwrite_by_default():
    tls_context = mock.MagicMock(__nonzero__=lambda *args: False, __bool__=lambda *args: False)
    socket = mock.MagicMock()
    conn = HanaConnection("localhost", 8000, 'foo', 'bar', tls_context=tls_context)
    with mock.patch('socket.create_connection', mock.MagicMock(return_value=socket)):
        socket.recv.return_value = b'12345678'
        tls_context.wrap_socket.return_value = socket
        with pytest.raises(Exception, match='Invalid message header received'):
            conn.connect()
        tls_context.wrap_socket.assert_not_called()
