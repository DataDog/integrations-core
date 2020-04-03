# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
GLOBAL_METRICS = (
    'proxysql.active_transactions',
    'proxysql.query_processor_time_pct',
    'proxysql.questions',
    'proxysql.slow_queries',
    'proxysql.uptime',
    'proxysql.memory.sqlite3_memory_bytes',
    'proxysql.client.connections_aborted',
    'proxysql.client.connections_connected',
    'proxysql.client.connections_created',
    'proxysql.client.connections_non_idle',
    'proxysql.server.connections_aborted',
    'proxysql.server.connections_connected',
    'proxysql.server.connections_created',
    'proxysql.backend.query_time_pct',
    'proxysql.mysql.backend_buffers_bytes',
    'proxysql.mysql.frontend_buffers_bytes',
    'proxysql.mysql.session_internal_bytes',
    'proxysql.mysql.thread_workers',
    'proxysql.mysql.monitor_workers',
    'proxysql.pool.conn_success',
    'proxysql.pool.conn_failure',
    'proxysql.pool.conn_immediate',
    'proxysql.pool.memory_bytes',
    'proxysql.client.statements.active_total',
    'proxysql.client.statements.active_unique',
    'proxysql.server.statements.active_total',
    'proxysql.server.statements.active_unique',
    'proxysql.statements.cached',
    'proxysql.query_cache.entries',
    'proxysql.query_cache.memory_bytes',
    'proxysql.query_cache.purged',
    'proxysql.query_cache.bytes_in',
    'proxysql.query_cache.bytes_out',
    'proxysql.query_cache.get.count',
    'proxysql.query_cache.get_ok.count',
    'proxysql.query_cache.set.count',
)

COMMANDS_COUNTERS_METRICS = (
    'proxysql.performance.command.total_time_pct',
    'proxysql.performance.command.total_count',
    'proxysql.performance.command.cnt_100us',
    'proxysql.performance.command.cnt_500us',
    'proxysql.performance.command.cnt_1ms',
    'proxysql.performance.command.cnt_5ms',
    'proxysql.performance.command.cnt_10ms',
    'proxysql.performance.command.cnt_50ms',
    'proxysql.performance.command.cnt_100ms',
    'proxysql.performance.command.cnt_500ms',
    'proxysql.performance.command.cnt_1s',
    'proxysql.performance.command.cnt_5s',
    'proxysql.performance.command.cnt_10s',
    'proxysql.performance.command.cnt_infs',
)

CONNECTION_POOL_METRICS = (
    'proxysql.pool.connections_used',
    'proxysql.pool.connections_free',
    'proxysql.pool.connections_ok',
    'proxysql.pool.connections_error',
    'proxysql.pool.queries',
    'proxysql.pool.bytes_data_sent',
    'proxysql.pool.bytes_data_recv',
    'proxysql.pool.latency_ms',
)

USER_TAGS_METRICS = (
    'proxysql.frontend.user_connections',
    'proxysql.frontend.user_max_connections',
)


MEMORY_METRICS = (
    'proxysql.memory.jemalloc_resident',
    'proxysql.memory.jemalloc_active',
    'proxysql.memory.jemalloc_allocated',
    'proxysql.memory.jemalloc_mapped',
    'proxysql.memory.jemalloc_metadata',
    'proxysql.memory.jemalloc_retained',
    'proxysql.memory.auth_memory',
    'proxysql.memory.query_digest_memory',
    'proxysql.memory.stack_memory_mysql_threads',
    'proxysql.memory.stack_memory_admin_threads',
    'proxysql.memory.stack_memory_cluster_threads',
)

QUERY_RULES_TAGS_METRICS = ('proxysql.query_rules.rule_hits',)


ALL_METRICS = (
    GLOBAL_METRICS
    + MEMORY_METRICS
    + COMMANDS_COUNTERS_METRICS
    + CONNECTION_POOL_METRICS
    + USER_TAGS_METRICS
    + QUERY_RULES_TAGS_METRICS
)
