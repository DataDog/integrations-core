# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import CLICKHOUSE_VERSION
from .metrics import OPTIONAL_METRICS, get_metrics

pytestmark = pytest.mark.e2e


def test_check(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)
    server_tag = 'server:{}'.format(instance['server'])
    port_tag = 'port:{}'.format(instance['port'])
    metrics = get_metrics(CLICKHOUSE_VERSION)

    for metric in metrics:
        aggregator.assert_metric_has_tag(metric, server_tag, at_least=1)
        aggregator.assert_metric_has_tag(metric, port_tag, at_least=1)
        aggregator.assert_metric_has_tag(metric, 'db:default', at_least=1)
        aggregator.assert_metric_has_tag(metric, 'foo:bar', at_least=1)

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_metric(
        'clickhouse.dictionary.item.current',
        tags=[server_tag, port_tag, 'db:default', 'foo:bar', 'dictionary:test'],
        at_least=1,
    )

    for metric in OPTIONAL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_enforce_readonly_queries_setting(dd_agent_check, instance, clickhouse_conn):
    """
    Test that enforce_readonly_queries setting controls write access.

    Verifies by comparing actual outcomes (metrics collected, rows inserted)
    with and without the setting enabled.
    """
    from datadog_checks.base import AgentCheck

    # ==================================================================
    # SETUP: Create test table for write verification
    # ==================================================================
    clickhouse_conn.command('CREATE TABLE IF NOT EXISTS test_readonly_check (id UInt32) ENGINE = Memory')
    clickhouse_conn.command('TRUNCATE TABLE test_readonly_check')

    # ==================================================================
    # PHASE 1: Read query WITH enforce_readonly_queries=True (default)
    # Expected: Metrics ARE collected (reads work)
    # ==================================================================
    instance['enforce_readonly_queries'] = True
    instance['custom_queries'] = [
        {
            'query': 'SELECT count() FROM system.tables',
            'columns': [{'name': 'table_count', 'type': 'gauge'}],
            'tags': ['test:read_enabled'],
        }
    ]

    aggregator = dd_agent_check(instance)
    aggregator.assert_service_check('clickhouse.can_connect', status=AgentCheck.OK)
    aggregator.assert_metric('clickhouse.table_count', at_least=1)

    # ==================================================================
    # PHASE 2: Write query WITH enforce_readonly_queries=True
    # Expected: Row is NOT inserted (table remains empty)
    # ==================================================================
    instance['custom_queries'] = [
        {
            'query': 'INSERT INTO test_readonly_check VALUES (1)',
            'columns': [{'name': 'result', 'type': 'gauge'}],
            'tags': ['test:write_blocked'],
        }
    ]

    dd_agent_check(instance)

    result = clickhouse_conn.query('SELECT count() FROM test_readonly_check')
    row_count = result.result_rows[0][0]
    assert row_count == 0, (
        f"Expected 0 rows (write blocked) but found {row_count}. "
        f"Write should be blocked when enforce_readonly_queries=True"
    )

    # ==================================================================
    # PHASE 3: Read query WITHOUT enforce_readonly_queries=False
    # Expected: Metrics ARE collected (reads still work)
    # ==================================================================
    instance['enforce_readonly_queries'] = False
    instance['custom_queries'] = [
        {
            'query': 'SELECT count() FROM system.tables',
            'columns': [{'name': 'table_count', 'type': 'gauge'}],
            'tags': ['test:read_disabled'],
        }
    ]

    aggregator = dd_agent_check(instance)
    aggregator.assert_metric('clickhouse.table_count', at_least=1)

    # ==================================================================
    # PHASE 4: Write query WITHOUT enforce_readonly_queries=False
    # Expected: Row IS inserted (table has 1 row)
    # This proves OUR setting controls access, not DB user permissions
    # ==================================================================
    clickhouse_conn.command('TRUNCATE TABLE test_readonly_check')

    instance['custom_queries'] = [
        {
            'query': 'INSERT INTO test_readonly_check VALUES (999)',
            'columns': [{'name': 'result', 'type': 'gauge'}],
            'tags': ['test:write_allowed'],
        }
    ]

    dd_agent_check(instance)

    result = clickhouse_conn.query('SELECT count() FROM test_readonly_check')
    row_count = result.result_rows[0][0]
    assert row_count == 1, (
        f"Expected 1 row (write succeeded) but found {row_count}. "
        f"Write should succeed when enforce_readonly_queries=False. "
        f"If this fails, DB user may lack write permissions."
    )

    # ==================================================================
    # CLEANUP
    # ==================================================================
    clickhouse_conn.command('DROP TABLE test_readonly_check')
