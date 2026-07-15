# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Top queries by CPU time in the most recent completed 1-minute window.
# SPANNER_SYS.QUERY_STATS_TOP_MINUTE retains at least 6 hours of data, so
# filtering to MAX(INTERVAL_END) ensures each check run reads only the single
# latest completed minute rather than re-sending hours of historical rows.
# SPANNER_SYS tables are only available on real Spanner instances — the emulator
# does not support them.
QUERY_STATS_TOP_MINUTE = """
SELECT
  INTERVAL_END,
  REQUEST_TAG,
  QUERY_TYPE,
  TEXT,
  TEXT_TRUNCATED,
  TEXT_FINGERPRINT,
  EXECUTION_COUNT,
  AVG_LATENCY_SECONDS,
  AVG_ROWS,
  AVG_BYTES,
  AVG_ROWS_SCANNED,
  AVG_CPU_SECONDS,
  ALL_FAILED_EXECUTION_COUNT,
  ALL_FAILED_AVG_LATENCY_SECONDS,
  CANCELLED_OR_DISCONNECTED_EXECUTION_COUNT,
  TIMED_OUT_EXECUTION_COUNT
FROM SPANNER_SYS.QUERY_STATS_TOP_MINUTE
WHERE INTERVAL_END = (SELECT MAX(INTERVAL_END) FROM SPANNER_SYS.QUERY_STATS_TOP_MINUTE)
ORDER BY AVG_CPU_SECONDS DESC
"""

# Column positions in the result set above, kept in sync with the SELECT list.
QUERY_STATS_COLUMNS = (
    'interval_end',
    'request_tag',
    'query_type',
    'text',
    'text_truncated',
    'text_fingerprint',
    'execution_count',
    'avg_latency_seconds',
    'avg_rows',
    'avg_bytes',
    'avg_rows_scanned',
    'avg_cpu_seconds',
    'all_failed_execution_count',
    'all_failed_avg_latency_seconds',
    'cancelled_or_disconnected_execution_count',
    'timed_out_execution_count',
)
