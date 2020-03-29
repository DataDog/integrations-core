# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import psycopg2
import pytest

from datadog_checks.pgbouncer import PgBouncer

from . import common


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_check(instance, aggregator, datadog_agent):
    # add some stats
    connection = psycopg2.connect(
        host=common.HOST,
        port=common.PORT,
        user=common.USER,
        password=common.PASS,
        database=common.DB,
        connect_timeout=1,
    )
    connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = connection.cursor()
    cur.execute('SELECT * FROM persons;')

    # run the check
    check = PgBouncer('pgbouncer', {}, [instance])
    check.check_id = 'test:123'
    check.check(instance)

    version = _get_version_from_env()
    assert_metric_coverage(version, aggregator)
    patch = '1' if version[1] == '8' else '2'

    version_metadata = {
        'version.raw': '.'.join(version) + '.' + patch,
        'version.scheme': 'semver',
        'version.major': version[0],
        'version.minor': version[1],
        'version.patch': patch,
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


def _get_version_from_env():
    return os.environ.get('PGBOUNCER_VERSION').split('_')


@pytest.mark.e2e
def test_check_e2e(dd_agent_check, instance):
    # run the check
    aggregator = dd_agent_check(instance, rate=True)
    version = _get_version_from_env()
    assert_metric_coverage(version, aggregator)


def assert_metric_coverage(version, aggregator):
    aggregator.assert_metric('pgbouncer.pools.cl_active')
    aggregator.assert_metric('pgbouncer.pools.cl_waiting')
    aggregator.assert_metric('pgbouncer.pools.sv_active')
    aggregator.assert_metric('pgbouncer.pools.sv_idle')
    aggregator.assert_metric('pgbouncer.pools.sv_used')
    aggregator.assert_metric('pgbouncer.pools.sv_tested')
    aggregator.assert_metric('pgbouncer.pools.sv_login')
    aggregator.assert_metric('pgbouncer.pools.maxwait')
    aggregator.assert_metric('pgbouncer.pools.maxwait_us')
    aggregator.assert_metric('pgbouncer.stats.avg_recv')
    aggregator.assert_metric('pgbouncer.stats.avg_sent')
    aggregator.assert_metric('pgbouncer.stats.total_wait_time')
    aggregator.assert_metric('pgbouncer.stats.avg_wait_time')

    pgbouncer_pre18 = int(version[1]) < 8
    if pgbouncer_pre18:
        aggregator.assert_metric('pgbouncer.stats.avg_req')
        aggregator.assert_metric('pgbouncer.stats.avg_query')
        aggregator.assert_metric('pgbouncer.stats.requests_per_second')
    else:
        aggregator.assert_metric('pgbouncer.stats.avg_transaction_time')
        aggregator.assert_metric('pgbouncer.stats.avg_query_time')
        aggregator.assert_metric('pgbouncer.stats.avg_transaction_count')
        aggregator.assert_metric('pgbouncer.stats.avg_query_count')
        aggregator.assert_metric('pgbouncer.stats.queries_per_second')
        aggregator.assert_metric('pgbouncer.stats.transactions_per_second')
        aggregator.assert_metric('pgbouncer.stats.total_transaction_time')

    aggregator.assert_metric('pgbouncer.stats.total_query_time')
    aggregator.assert_metric('pgbouncer.stats.bytes_received_per_second')
    aggregator.assert_metric('pgbouncer.stats.bytes_sent_per_second')

    aggregator.assert_metric('pgbouncer.databases.pool_size')
    aggregator.assert_metric('pgbouncer.databases.max_connections')
    aggregator.assert_metric('pgbouncer.databases.current_connections')

    # Service checks
    sc_tags = ['host:{}'.format(common.HOST), 'port:{}'.format(common.PORT), 'db:pgbouncer', 'optional:tag1']
    aggregator.assert_service_check(PgBouncer.SERVICE_CHECK_NAME, status=PgBouncer.OK, tags=sc_tags)
    aggregator.assert_all_metrics_covered()
