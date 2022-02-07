# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import certifi
import mock
import pytest

from datadog_checks.sap_hana import SapHanaCheck
from datadog_checks.sap_hana.connection import HanaConnection

from .common import requires_legacy_library, requires_proprietary_library

pytestmark = pytest.mark.unit


def error(*args, **kwargs):
    raise Exception('test')


def test_error_query(instance, dd_run_check):
    check = SapHanaCheck('sap_hana', {}, [instance])
    check.log = mock.MagicMock()

    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.execute = error
    conn.cursor = lambda: cursor
    check._conn = conn

    dd_run_check(check)
    check.log.error.assert_any_call('Error querying %s: %s', 'SYS.M_DATABASE', 'test')


def test_error_unknown(instance, dd_run_check):
    def query_master_database():
        error()

    check = SapHanaCheck('sap_hana', {}, [instance])
    check.log = mock.MagicMock()

    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.execute = error
    conn.cursor = lambda: cursor
    check._conn = conn

    check._default_methods.append(query_master_database)

    dd_run_check(check)
    check.log.exception.assert_any_call('Unexpected error running `%s`: %s', 'query_master_database', 'test')


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


@requires_legacy_library
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


@requires_legacy_library
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


@requires_legacy_library
@pytest.mark.parametrize(
    'init_config, instance_config, default_instance, persist',
    [
        pytest.param({'persist_db_connections': False}, None, True, False, id='Test option set in init_config'),
        pytest.param({}, False, False, False, id='Test option set in instance'),
        pytest.param({'persist_db_connections': False}, True, False, True, id='Test instance override'),
        pytest.param({}, None, True, True, id='Test instance default behavior'),
    ],
)
def test_persisted_db_connection(
    instance, dd_run_check, caplog, init_config, instance_config, persist, default_instance
):
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    expected_message = 'Refreshing database connection.'
    if not default_instance:
        instance['persist_db_connections'] = instance_config
    check = SapHanaCheck('sap_hana', init_config, [instance])
    dd_run_check(check)
    if persist:
        assert expected_message not in caplog.text
    else:
        assert expected_message in caplog.text
    assert check._persist_db_connections == persist


@requires_proprietary_library
class TestConnectionProperties:
    def test_default(self, instance):
        check = SapHanaCheck('sap_hana', {}, [instance])

        with mock.patch('datadog_checks.sap_hana.sap_hana.HanaConnection') as m:
            check.get_connection()
            m.assert_called_once_with(
                address=instance['server'],
                port=instance['port'],
                user=instance['username'],
                password=instance['password'],
                communicationTimeout=10000,
                nodeConnectTimeout=10000,
            )

    def test_defined(self, instance):
        instance = instance.copy()
        instance['timeout'] = 5
        instance['connection_properties'] = {
            'address': 'foobar',
            'nodeConnectTimeout': 1234,
            'key': 'hdbuserid',
            'sslUseDefaultTrustStore': False,
            'foo': ['bar', 'baz'],
        }
        check = SapHanaCheck('sap_hana', {}, [instance])

        with mock.patch('datadog_checks.sap_hana.sap_hana.HanaConnection') as m:
            check.get_connection()
            m.assert_called_once_with(
                address='foobar',
                port=instance['port'],
                user=instance['username'],
                password=instance['password'],
                communicationTimeout=5000,
                nodeConnectTimeout=1234,
                key='hdbuserid',
                sslUseDefaultTrustStore=False,
                foo=['bar', 'baz'],
            )

    def test_tls(self, instance):
        instance = instance.copy()
        instance['use_tls'] = True
        instance['connection_properties'] = {
            'key': 'hdbuserid',
            'sslUseDefaultTrustStore': False,
            'foo': ['bar', 'baz'],
        }
        check = SapHanaCheck('sap_hana', {}, [instance])

        with mock.patch('datadog_checks.sap_hana.sap_hana.HanaConnection') as m:
            check.get_connection()
            m.assert_called_once_with(
                address=instance['server'],
                port=instance['port'],
                user=instance['username'],
                password=instance['password'],
                communicationTimeout=10000,
                nodeConnectTimeout=10000,
                encrypt=True,
                sslHostNameInCertificate=instance['server'],
                sslSNIHostname=instance['server'],
                sslTrustStore=certifi.where(),
                key='hdbuserid',
                sslUseDefaultTrustStore=False,
                foo=['bar', 'baz'],
            )
