# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.sap_hana import SapHanaCheck

pytestmark = pytest.mark.unit


def test_error_query(instance):
    def error(_query):
        raise Exception('test')

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
        raise Exception('test')

    check = SapHanaCheck('sap_hana', {}, [instance])
    check.log = mock.MagicMock()
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
    log.error.assert_any_call('Custom query result expected 1 column(s), got 2')
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
    log.error.assert_any_call('Column field `type` is required for column `foo`')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    # Unknown type
    column_2['type'] = 'unknown'

    check.query_custom()
    log.error.assert_any_call('Invalid submission method `unknown` for metric column `foo`')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    # Non-numeric value
    column_2['type'] = 'gauge'

    check.query_custom()
    log.error.assert_any_call('Non-numeric value `bar` for metric column `foo`')
    log.reset_mock()
    cursor.fetchmany = rows_generator()

    gauge.assert_not_called()
