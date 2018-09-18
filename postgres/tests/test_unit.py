# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
from mock import MagicMock

# Mark the entire module as tests of type `unit`
pytestmark = pytest.mark.unit

KEY = ('localhost', '5432', 'dbname')


def test_get_instance_metrics_lt_92(check):
    """
    check output when 9.2+
    """
    check._is_9_2_or_above.return_value = False
    res = check._get_instance_metrics(KEY, 'dbname', False, False)
    assert res['metrics'] == check.COMMON_METRICS


def test_get_instance_metrics_92(check):
    """
    check output when <9.2
    """
    check._is_9_2_or_above.return_value = True
    res = check._get_instance_metrics(KEY, 'dbname', False, False)
    assert res['metrics'] == dict(check.COMMON_METRICS, **check.NEWER_92_METRICS)


def test_get_instance_metrics_state(check):
    """
    Ensure data is consistent when the function is called more than once
    """
    res = check._get_instance_metrics(KEY, 'dbname', False, False)
    assert res['metrics'] == dict(check.COMMON_METRICS, **check.NEWER_92_METRICS)
    check._is_9_2_or_above.side_effect = Exception  # metrics were cached so this shouldn't be called
    res = check._get_instance_metrics(KEY, 'dbname', [], False)
    assert res['metrics'] == dict(check.COMMON_METRICS, **check.NEWER_92_METRICS)

    # also check what happens when `metrics` is not valid
    check.instance_metrics[KEY] = []
    res = check._get_instance_metrics(KEY, 'dbname', False, False)
    assert res is None


def test_get_instance_metrics_database_size_metrics(check):
    """
    Test the function behaves correctly when `database_size_metrics` is passed
    """
    expected = check.COMMON_METRICS
    expected.update(check.NEWER_92_METRICS)
    expected.update(check.DATABASE_SIZE_METRICS)
    res = check._get_instance_metrics(KEY, 'dbname', True, False)
    assert res['metrics'] == expected


def test_get_instance_with_default(check):
    """
    Test the contents of the query string with different `collect_default_db` values
    """
    collect_default_db = False
    res = check._get_instance_metrics(KEY, 'dbname', False, collect_default_db)
    assert "  AND datname not ilike 'postgres'" in res['query']

    collect_default_db = True
    res = check._get_instance_metrics(KEY, 'dbname', False, collect_default_db)
    assert "  AND datname not ilike 'postgres'" not in res['query']


def test_get_instance_metrics_instance(check):
    """
    Test the caching system preventing instance metrics to be collected more than
    once when two instances are configured for the same server but different databases
    """
    res = check._get_instance_metrics(KEY, 'dbname', False, False)
    assert res is not None
    # 2nd round, same host/port combo: we shouldn't collect anything
    another = ('localhost', '5432', 'FOO')
    res = check._get_instance_metrics(another, 'dbname', False, False)
    assert res is None
    assert check.instance_metrics[another] == []


def test_get_version(check):
    """
    Test _get_version() to make sure the check is properly parsing Postgres versions
    """
    db = MagicMock()

    # Test #.#.# style versions
    db.cursor().fetchone.return_value = ['9.5.3']
    assert check._get_version('regular_version', db) == [9, 5, 3]

    # Test #.# style versions
    db.cursor().fetchone.return_value = ['10.2']
    assert check._get_version('short_version', db) == [10, 2]

    # Test #beta# style versions
    db.cursor().fetchone.return_value = ['11beta3']
    assert check._get_version('beta_version', db) == [11, -1, 3]

    # Test #unknown# style versions
    db.cursor().fetchone.return_value = ['11nightly3']
    assert check._get_version('unknown_version', db) == '11nightly3'


def test_is_above(check):
    """
    Test _is_above() to make sure the check is properly determining order of versions
    """
    db = MagicMock()

    # Test major versions
    db.cursor().fetchone.return_value = ['10.5.4']
    assert check._is_above('smaller major', db, [9, 5, 4])
    assert check._is_above('larger major', db, [11, 0, 0]) is False

    # Test minor versions
    db.cursor().fetchone.return_value = ['10.5.4']
    assert check._is_above('smaller minor', db, [10, 4, 4])
    assert check._is_above('larger minor', db, [10, 6, 4]) is False

    # Test patch versions
    db.cursor().fetchone.return_value = ['10.5.4']
    assert check._is_above('smaller patch', db, [10, 5, 3])
    assert check._is_above('larger patch', db, [10, 5, 5]) is False

    # Test same version, _is_above() returns True for greater than or equal to
    db.cursor().fetchone.return_value = ['10.5.4']
    assert check._is_above('same_version', db, [10, 5, 4])

    # Test beta version above
    db.cursor().fetchone.return_value = ['11beta4']
    assert check._is_above('newer_beta_version', db, [11, -1, 3])

    # Test beta version against official version
    db.cursor().fetchone.return_value = ['11.0.0']
    assert check._is_above('official_release', db, [11, -1, 3])

    # Test versions of unequal length
    db.cursor().fetchone.return_value = ['10.0']
    assert check._is_above('unequal_length', db, [10, 0])
    assert check._is_above('unequal_length', db, [10, 0, 0])
    assert check._is_above('unequal_length', db, [10, 0, 1]) is False

    # Test return value is not a list
    db.cursor().fetchone.return_value = "foo"
    assert check._is_above('smth not a list', db, [10, 0]) is False


def test_malformed_get_custom_queries(check):
    """
    Test early-exit conditions for _get_custom_queries()
    """
    check.log = MagicMock()
    db = MagicMock()
    programming_error = Exception

    malformed_custom_query = {}

    # Make sure 'metric_prefix' is defined
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("custom query field `metric_prefix` is required")
    check.log.reset_mock()

    # Make sure 'query' is defined
    malformed_custom_query['metric_prefix'] = 'postgresql'
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("custom query field `query` is required for metric_prefix `{}`".format(
                                            malformed_custom_query['metric_prefix']))
    check.log.reset_mock()

    # Make sure 'columns' is defined
    malformed_custom_query['query'] = 'SELECT num FROM sometable'
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("custom query field `columns` is required for metric_prefix `{}`".format(
                                            malformed_custom_query['metric_prefix']))
    check.log.reset_mock()

    # Make sure we gracefully handle an error while performing custom queries
    malformed_custom_query_column = {}
    malformed_custom_query['columns'] = [malformed_custom_query_column]
    db.cursor().execute.side_effect = programming_error
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("Error executing query for metric_prefix {}: ".format(
                                            malformed_custom_query['metric_prefix']))
    check.log.reset_mock()

    # Make sure the number of columns defined is the same as the number of columns return by the query
    malformed_custom_query_column = {}
    malformed_custom_query['columns'] = [malformed_custom_query_column]
    query_return = ['num', 1337]
    db.cursor().execute.side_effect = None
    db.cursor().fetchone.return_value = query_return
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("query result for metric_prefix {}: expected {} columns, got {}".format(
                                            malformed_custom_query['metric_prefix'],
                                            len(malformed_custom_query['columns']), len(query_return)))
    check.log.reset_mock()

    # Make sure the query does not return an empty result
    db.cursor().fetchone.return_value = []
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.debug.assert_called_with("query result for metric_prefix {}: returned an empty result".format(
                                       malformed_custom_query['metric_prefix']))
    check.log.reset_mock()

    # Make sure 'name' is defined in each column
    malformed_custom_query_column['some_key'] = 'some value'
    db.cursor().fetchone.return_value = [1337]
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("column field `name` is required for metric_prefix `{}`".format(
                                            malformed_custom_query['metric_prefix']))
    check.log.reset_mock()

    # Make sure 'type' is defined in each column
    malformed_custom_query_column['name'] = 'num'
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("column field `type` is required for column `{}` "
                                            "of metric_prefix `{}`".format(malformed_custom_query_column['name'],
                                                                           malformed_custom_query['metric_prefix']))
    check.log.reset_mock()

    # Make sure 'type' is a valid metric type
    malformed_custom_query_column['type'] = 'invalid_type'
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("invalid submission method `{}` for column `{}` of "
                                            "metric_prefix `{}`".format(malformed_custom_query_column['type'],
                                                                        malformed_custom_query_column['name'],
                                                                        malformed_custom_query['metric_prefix']))
    check.log.reset_mock()

    # Make sure we're only collecting numeric value metrics
    malformed_custom_query_column['type'] = 'gauge'
    query_return = MagicMock()
    query_return.__float__.side_effect = ValueError('Mocked exception')
    db.cursor().fetchone.return_value = [query_return]
    check._get_custom_queries(db, [], [malformed_custom_query], programming_error)
    check.log.error.assert_called_once_with("non-numeric value `{}` for metric column `{}` of "
                                            "metric_prefix `{}`".format(query_return,
                                                                        malformed_custom_query_column['name'],
                                                                        malformed_custom_query['metric_prefix']))
