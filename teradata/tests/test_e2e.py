# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck

from .common import (
    DEFAULT_METRICS,
    E2E_EXCLUDE_METRICS,
    EXPECTED_TAGS,
    ON_CI,
    RES_USAGE_METRICS,
    SERVICE_CHECK_CONNECT,
    SERVICE_CHECK_QUERY,
    TABLE_DISK_METRICS,
    TERADATA_SERVER,
    USE_TD_SANDBOX,
)

skip_on_ci = pytest.mark.skipif(ON_CI and not USE_TD_SANDBOX, reason='Do not run E2E test on sandbox environment')


@pytest.mark.skipif(USE_TD_SANDBOX, reason='Test only available for non-sandbox environments')
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception, match="Hostname lookup failed"):
        dd_agent_check(instance)
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.CRITICAL, count=1, tags=EXPECTED_TAGS)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, count=0)


@pytest.mark.skipif(not USE_TD_SANDBOX, reason='Test only available for sandbox environments')
@pytest.mark.e2e
def test_e2e_sandbox(dd_agent_check, aggregator, instance):
    global_tags = ['teradata_port:1025', 'teradata_server:{}'.format(TERADATA_SERVER)]
    disk_tag_prefixes = ['td_amp', 'td_account', 'td_database']
    table_disk_tag_prefixes = ['td_amp', 'td_account', 'td_database', 'td_table']
    amp_tag_prefixes = ['td_amp', 'td_account', 'td_user']

    aggregator = dd_agent_check()

    for metric in DEFAULT_METRICS:
        if metric not in E2E_EXCLUDE_METRICS:
            aggregator.assert_metric(metric, at_least=1)
            if 'teradata.disk_space' in metric:
                for prefix in disk_tag_prefixes:
                    aggregator.assert_metric_has_tag_prefix(metric, prefix, at_least=1)
            elif 'teradata.amp' in metric:
                for prefix in amp_tag_prefixes:
                    aggregator.assert_metric_has_tag_prefix(metric, prefix, at_least=1)

    for metric in RES_USAGE_METRICS:
        if metric not in E2E_EXCLUDE_METRICS:
            # assert at_least=0 to account for potential clock drift in the sandbox VM
            aggregator.assert_metric(metric, at_least=0, tags=global_tags)

    for metric in TABLE_DISK_METRICS:
        if metric not in E2E_EXCLUDE_METRICS:
            aggregator.assert_metric(metric, at_least=1)
            for prefix in table_disk_tag_prefixes:
                aggregator.assert_metric_has_tag_prefix(metric, prefix, at_least=1)

    for tag in global_tags:
        aggregator.assert_metric_has_tag(metric, tag, at_least=1)

    # assert can_query service check at_least=0 to account for potential clock drift in sandbox VM
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, ServiceCheck.OK, count=1, tags=global_tags)
    aggregator.assert_service_check(SERVICE_CHECK_QUERY, ServiceCheck.OK, at_least=0, tags=global_tags)


@pytest.mark.skipif(not USE_TD_SANDBOX, reason='Test only available for sandbox environments')
@pytest.mark.e2e
def test_enforce_readonly_queries_setting(dd_agent_check, e2e_instance, teradata_conn):
    """
    Test that enforce_readonly_queries setting controls write access.

    Verifies by comparing actual outcomes (metrics collected, rows inserted)
    with and without the setting enabled.
    """
    from datadog_checks.base import AgentCheck

    # ==================================================================
    # SETUP: Create test table for write verification
    # ==================================================================
    cursor = teradata_conn.cursor()
    cursor.execute('CREATE TABLE test_readonly_check (id INTEGER)')
    cursor.execute('DELETE FROM test_readonly_check')
    teradata_conn.commit()

    # ==================================================================
    # PHASE 1: Read query WITH enforce_readonly_queries=True (default)
    # Expected: Metrics ARE collected (reads work)
    # ==================================================================
    e2e_instance['enforce_readonly_queries'] = True
    e2e_instance['custom_queries'] = [
        {
            'query': 'SELECT COUNT(*) AS table_count FROM DBC.TablesV',
            'columns': [{'name': 'table_count', 'type': 'gauge'}],
            'tags': ['test:read_enabled'],
        }
    ]

    aggregator = dd_agent_check(e2e_instance)
    aggregator.assert_service_check(SERVICE_CHECK_CONNECT, status=AgentCheck.OK)
    aggregator.assert_metric('teradata.table_count', at_least=1)

    # ==================================================================
    # PHASE 2: Write query WITH enforce_readonly_queries=True
    # Expected: Row is NOT inserted (table remains empty)
    # ==================================================================
    e2e_instance['custom_queries'] = [
        {
            'query': 'INSERT INTO test_readonly_check VALUES (1)',
            'columns': [{'name': 'result', 'type': 'gauge'}],
            'tags': ['test:write_blocked'],
        }
    ]

    dd_agent_check(e2e_instance)

    cursor.execute('SELECT COUNT(*) FROM test_readonly_check')
    row_count = cursor.fetchone()[0]
    assert row_count == 0, (
        f"Expected 0 rows (write blocked) but found {row_count}. "
        f"Write should be blocked when enforce_readonly_queries=True"
    )

    # ==================================================================
    # PHASE 3: Read query WITHOUT enforce_readonly_queries=False
    # Expected: Metrics ARE collected (reads still work)
    # ==================================================================
    e2e_instance['enforce_readonly_queries'] = False
    e2e_instance['custom_queries'] = [
        {
            'query': 'SELECT COUNT(*) AS table_count FROM DBC.TablesV',
            'columns': [{'name': 'table_count', 'type': 'gauge'}],
            'tags': ['test:read_disabled'],
        }
    ]

    aggregator = dd_agent_check(e2e_instance)
    aggregator.assert_metric('teradata.table_count', at_least=1)

    # ==================================================================
    # PHASE 4: Write query WITHOUT enforce_readonly_queries=False
    # Expected: Row IS inserted (table has 1 row)
    # This proves OUR setting controls access, not DB user permissions
    # ==================================================================
    cursor.execute('DELETE FROM test_readonly_check')
    teradata_conn.commit()

    e2e_instance['custom_queries'] = [
        {
            'query': 'INSERT INTO test_readonly_check VALUES (999)',
            'columns': [{'name': 'result', 'type': 'gauge'}],
            'tags': ['test:write_allowed'],
        }
    ]

    dd_agent_check(e2e_instance)

    cursor.execute('SELECT COUNT(*) FROM test_readonly_check')
    row_count = cursor.fetchone()[0]
    assert row_count == 1, (
        f"Expected 1 row (write succeeded) but found {row_count}. "
        f"Write should succeed when enforce_readonly_queries=False. "
        f"If this fails, DB user may lack write permissions."
    )

    # ==================================================================
    # CLEANUP
    # ==================================================================
    cursor.execute('DROP TABLE test_readonly_check')
    teradata_conn.commit()
    cursor.close()
