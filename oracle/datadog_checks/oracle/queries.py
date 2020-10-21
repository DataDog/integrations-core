# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.db import Query

ProcessMetrics = Query(
    {
        'name': 'process',
        'query': 'SELECT PROGRAM, PGA_USED_MEM, PGA_ALLOC_MEM, PGA_FREEABLE_MEM, PGA_MAX_MEM FROM GV$PROCESS',
        'columns': [
            {'name': 'program', 'type': 'tag'},
            {'name': 'process.pga_used_memory', 'type': 'gauge'},
            {'name': 'process.pga_allocated_memory', 'type': 'gauge'},
            {'name': 'process.pga_freeable_memory', 'type': 'gauge'},
            {'name': 'process.pga_maximum_memory', 'type': 'gauge'},
        ],
    }
)

SystemMetrics = Query(
    {
        'name': 'system',
        'query': 'SELECT VALUE, METRIC_NAME FROM GV$SYSMETRIC ORDER BY BEGIN_TIME',
        'columns': [
            {'name': 'value', 'type': 'source'},
            {
                'name': 'metric_name',
                'type': 'match',
                'source': 'value',
                'items': {
                    'Buffer Cache Hit Ratio': {'name': 'buffer_cachehit_ratio', 'type': 'gauge'},
                    'Cursor Cache Hit Ratio': {'name': 'cursor_cachehit_ratio', 'type': 'gauge'},
                    'Library Cache Hit Ratio': {'name': 'library_cachehit_ratio', 'type': 'gauge'},
                    'Shared Pool Free %': {'name': 'shared_pool_free', 'type': 'gauge'},
                    'Physical Reads Per Sec': {'name': 'physical_reads', 'type': 'gauge'},
                    'Physical Writes Per Sec': {'name': 'physical_writes', 'type': 'gauge'},
                    'Enqueue Timeouts Per Sec': {'name': 'enqueue_timeouts', 'type': 'gauge'},
                    'GC CR Block Received Per Second': {'name': 'gc_cr_block_received', 'type': 'gauge'},
                    'Global Cache Blocks Corrupted': {'name': 'cache_blocks_corrupt', 'type': 'gauge'},
                    'Global Cache Blocks Lost': {'name': 'cache_blocks_lost', 'type': 'gauge'},
                    'Logons Per Sec': {'name': 'logons', 'type': 'gauge'},
                    'Average Active Sessions': {'name': 'active_sessions', 'type': 'gauge'},
                    'Long Table Scans Per Sec': {'name': 'long_table_scans', 'type': 'gauge'},
                    'SQL Service Response Time': {'name': 'service_response_time', 'type': 'gauge'},
                    'User Rollbacks Per Sec': {'name': 'user_rollbacks', 'type': 'gauge'},
                    'Total Sorts Per User Call': {'name': 'sorts_per_user_call', 'type': 'gauge'},
                    'Rows Per Sort': {'name': 'rows_per_sort', 'type': 'gauge'},
                    'Disk Sort Per Sec': {'name': 'disk_sorts', 'type': 'gauge'},
                    'Memory Sorts Ratio': {'name': 'memory_sorts_ratio', 'type': 'gauge'},
                    'Database Wait Time Ratio': {'name': 'database_wait_time_ratio', 'type': 'gauge'},
                    'Session Limit %': {'name': 'session_limit_usage', 'type': 'gauge'},
                    'Session Count': {'name': 'session_count', 'type': 'gauge'},
                    'Temp Space Used': {'name': 'temp_space_used', 'type': 'gauge'},
                },
            },
        ],
    }
)
TableSpaceMetrics = Query(
    {
        'name': 'process',
        'query': """\
SELECT
  m.tablespace_name,
  NVL(m.used_space * t.block_size, 0),
  m.tablespace_size * t.block_size,
  NVL(m.used_percent, 0),
  NVL2(m.used_space, 0, 1)
FROM
  dba_tablespace_usage_metrics m
  join dba_tablespaces t on m.tablespace_name = t.tablespace_name
  """,
        'columns': [
            {'name': 'tablespace', 'type': 'tag'},
            {'name': 'tablespace.used', 'type': 'gauge'},
            {'name': 'tablespace.size', 'type': 'gauge'},
            {'name': 'tablespace.in_use', 'type': 'gauge'},
            {'name': 'tablespace.offline', 'type': 'gauge'},
        ],
    }
)
