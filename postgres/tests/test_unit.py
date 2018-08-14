# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

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
