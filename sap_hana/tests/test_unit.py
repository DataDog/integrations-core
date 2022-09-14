# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import certifi
import mock
import pytest

from datadog_checks.sap_hana import SapHanaCheck

from .common import TIMEOUT

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


def test_reconnect_on_connection_failure(instance, dd_run_check, aggregator):
    def connection_error(*args, **kwargs):
        raise Exception('Lost connection to HANA server')

    check = SapHanaCheck('sap_hana', {}, [instance])
    check.log = mock.MagicMock()

    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.execute = connection_error
    conn.cursor = lambda: cursor
    check._conn = conn

    dd_run_check(check)

    aggregator.assert_no_duplicate_service_checks()
    aggregator.assert_service_check("sap_hana.{}".format(SapHanaCheck.SERVICE_CHECK_CONNECT), SapHanaCheck.WARNING)
    conn.close.assert_called()
    check.log.error.assert_any_call('Error querying %s: %s', 'SYS.M_DATABASE', 'Lost connection to HANA server')

    # Assert than a connection is reattempted
    check.get_connection = mock.MagicMock()
    check.get_connection.return_value = conn
    dd_run_check(check)
    check.get_connection.assert_called()


def test_emits_critical_service_check_when_connection_flakes(instance, dd_run_check, aggregator):
    def connection_flakes(*args, **kwargs):
        raise Exception('Session has been reconnected after an error')

    check = SapHanaCheck('sap_hana', {}, [instance])
    check.log = mock.MagicMock()

    conn = mock.MagicMock()
    cursor = mock.MagicMock()
    cursor.execute = connection_flakes
    conn.cursor = lambda: cursor
    check._conn = conn

    dd_run_check(check)

    aggregator.assert_no_duplicate_service_checks()
    aggregator.assert_service_check("sap_hana.{}".format(SapHanaCheck.SERVICE_CHECK_CONNECT), SapHanaCheck.WARNING)
    check.log.error.assert_any_call(
        'Error querying %s: %s', 'SYS.M_DATABASE', 'Session has been reconnected after an error'
    )

    # Assert than a connection is not reattempted
    check.get_connection = mock.MagicMock()
    dd_run_check(check)
    check.get_connection.assert_not_called()


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


class TestConnectionProperties:
    def test_default(self, instance):
        del instance['timeout']  # to check default value
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
                communicationTimeout=TIMEOUT * 1000,
                nodeConnectTimeout=TIMEOUT * 1000,
                encrypt=True,
                sslHostNameInCertificate=instance['server'],
                sslSNIHostname=instance['server'],
                sslTrustStore=certifi.where(),
                key='hdbuserid',
                sslUseDefaultTrustStore=False,
                foo=['bar', 'baz'],
            )
