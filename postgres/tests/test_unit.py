# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import psycopg2
import pytest
from mock import MagicMock
from semver import VersionInfo

from datadog_checks.postgres import util

pytestmark = pytest.mark.unit


def test_get_instance_metrics_lt_92(check):
    """
    check output when 9.2+
    """
    check._version = VersionInfo(9, 1, 0)
    res = check._get_instance_metrics(False, False)
    assert res['metrics'] == util.COMMON_METRICS


def test_get_instance_metrics_92(check):
    """
    check output when <9.2
    """
    check._version = VersionInfo(9, 2, 0)
    res = check._get_instance_metrics(False, False)
    assert res['metrics'] == dict(util.COMMON_METRICS, **util.NEWER_92_METRICS)


def test_get_instance_metrics_state(check):
    """
    Ensure data is consistent when the function is called more than once
    """
    res = check._get_instance_metrics(False, False)
    assert res['metrics'] == dict(util.COMMON_METRICS, **util.NEWER_92_METRICS)
    check._version = 'foo'  # metrics were cached so this shouldn't be called
    res = check._get_instance_metrics([], False)
    assert res['metrics'] == dict(util.COMMON_METRICS, **util.NEWER_92_METRICS)


def test_get_instance_metrics_database_size_metrics(check):
    """
    Test the function behaves correctly when `database_size_metrics` is passed
    """
    expected = util.COMMON_METRICS
    expected.update(util.NEWER_92_METRICS)
    expected.update(util.DATABASE_SIZE_METRICS)
    res = check._get_instance_metrics(True, False)
    assert res['metrics'] == expected


def test_get_instance_with_default(check):
    """
    Test the contents of the query string with different `collect_default_db` values
    """
    collect_default_db = False
    res = check._get_instance_metrics(False, collect_default_db)
    assert "  AND psd.datname not ilike 'postgres'" in res['query']

    collect_default_db = True
    res = check._get_instance_metrics(False, collect_default_db)
    assert "  AND psd.datname not ilike 'postgres'" not in res['query']


def test_malformed_get_custom_queries(check):
    """
    Test early-exit conditions for _get_custom_queries()
    """
    check.log = MagicMock()
    db = MagicMock()
    check.db = db

    malformed_custom_query = {}

    # Make sure 'metric_prefix' is defined
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with("custom query field `metric_prefix` is required")
    check.log.reset_mock()

    # Make sure 'query' is defined
    malformed_custom_query['metric_prefix'] = 'postgresql'
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with(
        "custom query field `query` is required for metric_prefix `%s`", malformed_custom_query['metric_prefix']
    )
    check.log.reset_mock()

    # Make sure 'columns' is defined
    malformed_custom_query['query'] = 'SELECT num FROM sometable'
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with(
        "custom query field `columns` is required for metric_prefix `%s`", malformed_custom_query['metric_prefix']
    )
    check.log.reset_mock()

    # Make sure we gracefully handle an error while performing custom queries
    malformed_custom_query_column = {}
    malformed_custom_query['columns'] = [malformed_custom_query_column]
    db.cursor().execute.side_effect = psycopg2.ProgrammingError('FOO')
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with(
        "Error executing query for metric_prefix %s: %s", malformed_custom_query['metric_prefix'], 'FOO'
    )
    check.log.reset_mock()

    # Make sure the number of columns defined is the same as the number of columns return by the query
    malformed_custom_query_column = {}
    malformed_custom_query['columns'] = [malformed_custom_query_column]
    query_return = ['num', 1337]
    db.cursor().execute.side_effect = None
    db.cursor().__iter__.return_value = iter([query_return])
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with(
        "query result for metric_prefix %s: expected %s columns, got %s",
        malformed_custom_query['metric_prefix'],
        len(malformed_custom_query['columns']),
        len(query_return),
    )
    check.log.reset_mock()

    # Make sure the query does not return an empty result
    db.cursor().__iter__.return_value = iter([[]])
    check._get_custom_queries([], [malformed_custom_query])
    check.log.debug.assert_called_with(
        "query result for metric_prefix %s: returned an empty result", malformed_custom_query['metric_prefix']
    )
    check.log.reset_mock()

    # Make sure 'name' is defined in each column
    malformed_custom_query_column['some_key'] = 'some value'
    db.cursor().__iter__.return_value = iter([[1337]])
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with(
        "column field `name` is required for metric_prefix `%s`", malformed_custom_query['metric_prefix']
    )
    check.log.reset_mock()

    # Make sure 'type' is defined in each column
    malformed_custom_query_column['name'] = 'num'
    db.cursor().__iter__.return_value = iter([[1337]])
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with(
        "column field `type` is required for column `%s` of metric_prefix `%s`",
        malformed_custom_query_column['name'],
        malformed_custom_query['metric_prefix'],
    )
    check.log.reset_mock()

    # Make sure 'type' is a valid metric type
    malformed_custom_query_column['type'] = 'invalid_type'
    db.cursor().__iter__.return_value = iter([[1337]])
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with(
        "invalid submission method `%s` for column `%s` of metric_prefix `%s`",
        malformed_custom_query_column['type'],
        malformed_custom_query_column['name'],
        malformed_custom_query['metric_prefix'],
    )
    check.log.reset_mock()

    # Make sure we're only collecting numeric value metrics
    malformed_custom_query_column['type'] = 'gauge'
    query_return = MagicMock()
    query_return.__float__.side_effect = ValueError('Mocked exception')
    db.cursor().__iter__.return_value = iter([[query_return]])
    check._get_custom_queries([], [malformed_custom_query])
    check.log.error.assert_called_once_with(
        "non-numeric value `%s` for metric column `%s` of metric_prefix `%s`",
        query_return,
        malformed_custom_query_column['name'],
        malformed_custom_query['metric_prefix'],
    )
