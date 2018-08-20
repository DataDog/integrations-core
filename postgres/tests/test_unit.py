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


def test__get_version(check):
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


def test__is_above(check):
    """
    Test _is_above() to make sure the check is properly determining order of versions
    """
    db = MagicMock()

    # Test larger major versions
    db.cursor().fetchone.return_value = ['10.5.4']
    assert check._is_above('larger major', db, [9, 5, 4])

    # Test minor version larger
    db.cursor().fetchone.return_value = ['10.5.4']
    assert check._is_above('larger_minor', db, [9, 8, 4])

    # Test patch version larger
    db.cursor().fetchone.return_value = ['10.5.4']
    assert check._is_above('larger_patch', db, [9, 5, 8])

    # Test same version, _is_above() returns True for greater than or equal to
    db.cursor().fetchone.return_value = ['10.5.4']
    assert check._is_above('same_version', db, [10, 5, 4])

    # Test beta version above
    db.cursor().fetchone.return_value = ['11beta4']
    assert check._is_above('newer_beta_version', db, [11, -1, 3])

    # Test beta version against official version
    db.cursor().fetchone.return_value = ['11.0.0']
    assert check._is_above('official_release', db, [11, -1, 3])
