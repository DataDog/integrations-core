# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import mock
import psycopg2
import pytest
from pytest import fail
from semver import VersionInfo

from datadog_checks.postgres import PostgreSql, util

pytestmark = pytest.mark.unit


def test_get_instance_metrics_lt_92(integration_check, pg_instance):
    """
    check output when 9.2+
    """
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)

    res = check.metrics_cache.get_instance_metrics(VersionInfo(9, 1, 0))
    assert res['metrics'] == dict(util.COMMON_METRICS, **util.DBM_MIGRATED_METRICS)


def test_get_instance_metrics_92(integration_check, pg_instance):
    """
    check output when <9.2
    """
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)

    res = check.metrics_cache.get_instance_metrics(VersionInfo(9, 2, 0))
    c_metrics = dict(util.COMMON_METRICS, **util.DBM_MIGRATED_METRICS)
    assert res['metrics'] == dict(c_metrics, **util.NEWER_92_METRICS)


def test_get_instance_metrics_state(integration_check, pg_instance):
    """
    Ensure data is consistent when the function is called more than once
    """
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)

    res = check.metrics_cache.get_instance_metrics(VersionInfo(9, 2, 0))
    c_metrics = dict(util.COMMON_METRICS, **util.DBM_MIGRATED_METRICS)
    assert res['metrics'] == dict(c_metrics, **util.NEWER_92_METRICS)

    res = check.metrics_cache.get_instance_metrics('foo')  # metrics were cached so this shouldn't be called
    assert res['metrics'] == dict(c_metrics, **util.NEWER_92_METRICS)


def test_get_instance_metrics_database_size_metrics(integration_check, pg_instance):
    """
    Test the function behaves correctly when `database_size_metrics` is passed
    """
    pg_instance['collect_default_database'] = True
    pg_instance['collect_database_size_metrics'] = False
    check = integration_check(pg_instance)

    expected = util.COMMON_METRICS
    expected.update(util.DBM_MIGRATED_METRICS)
    expected.update(util.NEWER_92_METRICS)
    expected.update(util.DATABASE_SIZE_METRICS)
    res = check.metrics_cache.get_instance_metrics(VersionInfo(9, 2, 0))
    assert res['metrics'] == expected


@pytest.mark.parametrize("collect_default_database", [True, False])
def test_get_instance_with_default(pg_instance, collect_default_database):
    """
    Test the contents of the query string with different `collect_default_database` values
    """
    pg_instance['collect_default_database'] = collect_default_database
    check = PostgreSql('postgres', {}, [pg_instance])
    check.version = VersionInfo(9, 2, 0)
    res = check.metrics_cache.get_instance_metrics(check.version)
    dbfilter = " AND psd.datname not ilike 'postgres'"
    if collect_default_database:
        assert dbfilter not in res['query']
    else:
        assert dbfilter in res['query']


@pytest.mark.parametrize(
    'test_case, params',
    [
        ('9.6.2', {'version.major': '9', 'version.minor': '6', 'version.patch': '2'}),
        ('10.0', {'version.major': '10', 'version.minor': '0', 'version.patch': '0'}),
        (
            '11nightly3',
            {'version.major': '11', 'version.minor': '0', 'version.patch': '0', 'version.release': 'nightly.3'},
        ),
    ],
)
def test_version_metadata(check, test_case, params):
    check.check_id = 'test:123'
    with mock.patch('datadog_checks.base.stubs.datadog_agent.set_check_metadata') as m:
        check.set_metadata('version', test_case)
        for name, value in params.items():
            m.assert_any_call('test:123', name, value)
        m.assert_any_call('test:123', 'version.scheme', 'semver')
        m.assert_any_call('test:123', 'version.raw', test_case)


@pytest.mark.parametrize(
    'test_case',
    [
        ('any_hostname'),
    ],
)
def test_resolved_hostname_metadata(check, test_case):
    check.check_id = 'test:123'
    with mock.patch('datadog_checks.base.stubs.datadog_agent.set_check_metadata') as m:
        check.set_metadata('resolved_hostname', test_case)
        m.assert_any_call('test:123', 'resolved_hostname', test_case)


def test_query_timeout_connection_string(aggregator, integration_check, pg_instance):
    pg_instance['password'] = ''
    pg_instance['query_timeout'] = 1000

    check = integration_check(pg_instance)
    try:
        check.db_pool.get_connection(pg_instance['dbname'], 100)
    except psycopg2.ProgrammingError as e:
        fail(str(e))
    except psycopg2.OperationalError:
        # could not connect to server because there is no server running
        pass


@pytest.mark.parametrize(
    'disable_generic_tags, expected_tags',
    [
        (
            True,
            {
                'db:datadog_test',
                'port:5432',
                'foo:bar',
                'dd.internal.resource:database_instance:stubbed.hostname',
                'database_hostname:stubbed.hostname',
            },
        ),
        (
            False,
            {
                'db:datadog_test',
                'foo:bar',
                'port:5432',
                'server:localhost',
                'dd.internal.resource:database_instance:stubbed.hostname',
                'database_hostname:stubbed.hostname',
            },
        ),
    ],
)
def test_server_tag_(disable_generic_tags, expected_tags, pg_instance):
    instance = copy.deepcopy(pg_instance)
    instance['disable_generic_tags'] = disable_generic_tags
    check = PostgreSql('test_instance', {}, [instance])
    assert set(check.tags) == expected_tags


@pytest.mark.parametrize(
    'disable_generic_tags, expected_hostname', [(True, 'resolved.hostname'), (False, 'resolved.hostname')]
)
def test_resolved_hostname(disable_generic_tags, expected_hostname, pg_instance):
    instance = copy.deepcopy(pg_instance)
    instance['disable_generic_tags'] = disable_generic_tags

    with mock.patch(
        'datadog_checks.postgres.PostgreSql.resolve_db_host', return_value='resolved.hostname'
    ) as resolve_db_host_mock:
        check = PostgreSql('test_instance', {}, [instance])
        assert check.resolved_hostname == expected_hostname
        assert resolve_db_host_mock.called is True
