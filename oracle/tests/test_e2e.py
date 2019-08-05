# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

METRICS = [
    'oracle.process.pga_maximum_memory',
    'oracle.process.pga_used_memory',
    'oracle.process.pga_freeable_memory',
    'oracle.tablespace.in_use',
    'oracle.logons',
    'oracle.tablespace.used',
    'oracle.process.pga_allocated_memory',
    'oracle.tablespace.offline',
    'oracle.active_sessions',
    'oracle.temp_space_used',
    'oracle.physical_writes',
    'oracle.tablespace.size',
    'oracle.shared_pool_free',
    'oracle.library_cachehit_ratio',
    'oracle.memory_sorts_ratio',
    'oracle.buffer_cachehit_ratio',
    'oracle.physical_reads',
]


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()
    for metric in METRICS:
        aggregator.assert_metric(metric)
