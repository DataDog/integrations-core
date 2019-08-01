# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

METRICS = [
    'oracle.process.pga_maximum_memory',
    'oracle.process.pga_used_memory',
    'oracle.process.pga_freeable_memory',
    'oracle.cursor_cachehit_ratio',
    'oracle.tablespace.in_use',
    'oracle.logons',
    'oracle.tablespace.used',
    'oracle.user_rollbacks',
    'oracle.process.pga_allocated_memory',
    'oracle.tablespace.offline',
    'oracle.long_table_scans',
    'oracle.disk_sorts',
    'oracle.rows_per_sort',
    'oracle.session_limit_usage',
    'oracle.enqueue_timeouts',
    'oracle.sorts_per_user_call',
    'oracle.active_sessions',
    'oracle.temp_space_used',
    'oracle.gc_cr_block_received',
    'oracle.physical_writes',
    'oracle.tablespace.size',
    'oracle.database_wait_time_ratio',
    'oracle.session_count',
    'oracle.cache_blocks_lost',
    'oracle.shared_pool_free',
    'oracle.library_cachehit_ratio',
    'oracle.memory_sorts_ratio',
    'oracle.buffer_cachehit_ratio',
    'oracle.physical_reads',
    'oracle.cache_blocks_corrupt',
    'oracle.service_response_time',
]


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()
    for metric in METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
