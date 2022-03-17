# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.oracle import Oracle

METRICS = [
    'oracle.tablespace.used',
    # ProcessMetrics
    'oracle.process.pga_used_memory',
    'oracle.process.pga_allocated_memory',
    'oracle.process.pga_freeable_memory',
    'oracle.process.pga_maximum_memory',
    # SystemMetrics
    'oracle.buffer_cachehit_ratio',
    'oracle.cursor_cachehit_ratio',
    'oracle.library_cachehit_ratio',
    'oracle.shared_pool_free',
    'oracle.physical_reads',
    'oracle.physical_writes',
    'oracle.enqueue_timeouts',
    'oracle.gc_cr_block_received',
    'oracle.cache_blocks_corrupt',
    'oracle.cache_blocks_lost',
    'oracle.logons',
    'oracle.active_sessions',
    'oracle.long_table_scans',
    'oracle.service_response_time',
    'oracle.user_rollbacks',
    'oracle.sorts_per_user_call',
    'oracle.rows_per_sort',
    'oracle.disk_sorts',
    'oracle.memory_sorts_ratio',
    'oracle.database_wait_time_ratio',
    'oracle.session_limit_usage',
    'oracle.session_count',
    'oracle.temp_space_used',
    # TableSpaceMetrics
    'oracle.tablespace.in_use',
    'oracle.tablespace.size',
    'oracle.tablespace.in_use',
    'oracle.tablespace.offline',
]
SERVICE_CHECKS = ['oracle.can_connect', 'oracle.can_query']


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()
    for metric in METRICS:
        aggregator.assert_metric(metric)

    for service_check in SERVICE_CHECKS:
        aggregator.assert_service_check(service_check)
    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_bad_service_check(dd_agent_check, bad_instance):
    aggregator = dd_agent_check(bad_instance)
    aggregator.assert_service_check("oracle.can_connect", Oracle.CRITICAL)
