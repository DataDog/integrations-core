# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager
from datadog_checks.dev import get_docker_hostname

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
    'proxysql.pool.latency_us',
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

BACKENDS_METRICS = ('proxysql.backends.count',)

QUERY_RULES_TAGS_METRICS = ('proxysql.query_rules.rule_hits',)


ALL_METRICS = (
    GLOBAL_METRICS
    + MEMORY_METRICS
    + COMMANDS_COUNTERS_METRICS
    + CONNECTION_POOL_METRICS
    + USER_TAGS_METRICS
    + QUERY_RULES_TAGS_METRICS
)

DOCKER_HOST = get_docker_hostname()
MYSQL_PORT = 6612
PROXY_PORT = 6033
PROXY_ADMIN_PORT = 6032
MYSQL_USER = 'proxysql'
MYSQL_PASS = 'pass'
PROXY_ADMIN_USER = 'proxy'
PROXY_ADMIN_PASS = 'proxy'
PROXY_STATS_USER = 'proxystats'
PROXY_STATS_PASS = 'proxystats'
MYSQL_DATABASE = 'test'
PROXY_MAIN_DATABASE = 'main'
PROXYSQL_VERSION = os.environ['PROXYSQL_VERSION']

BASIC_INSTANCE = {
    'host': DOCKER_HOST,
    'port': PROXY_ADMIN_PORT,
    'username': PROXY_ADMIN_USER,
    'password': PROXY_ADMIN_PASS,
    'tags': ["application:test"],
    'additional_metrics': [],
}


BASIC_INSTANCE_TLS = {
    'host': DOCKER_HOST,
    'port': PROXY_ADMIN_PORT,
    'username': PROXY_ADMIN_USER,
    'password': PROXY_ADMIN_PASS,
    'tags': ["application:test"],
    'additional_metrics': [],
    'tls_verify': True,
    'tls_ca_cert': "/etc/ssl/certs/proxysql-ca.pem",
    'tls_validate_hostname': True,
}


INSTANCE_ALL_METRICS = {
    'host': DOCKER_HOST,
    'port': PROXY_ADMIN_PORT,
    'username': PROXY_ADMIN_USER,
    'password': PROXY_ADMIN_PASS,
    'tags': ["application:test"],
    'additional_metrics': [
        'command_counters_metrics',
        'connection_pool_metrics',
        'users_metrics',
        'memory_metrics',
        'query_rules_metrics',
    ],
}

INSTANCE_ALL_METRICS_STATS = {
    'host': DOCKER_HOST,
    'port': PROXY_ADMIN_PORT,
    'username': PROXY_STATS_USER,
    'password': PROXY_STATS_PASS,
    'database_name': PROXY_MAIN_DATABASE,
    'tags': ["application:test"],
    'additional_metrics': [
        'command_counters_metrics',
        'connection_pool_metrics',
        'users_metrics',
        'memory_metrics',
        'query_rules_metrics',
    ],
}


def mock_executor(result=()):
    def executor(_):
        return result

    return executor


def create_query_manager(*args, **kwargs):
    executor = kwargs.pop('executor', None)
    if executor is None:
        executor = mock_executor()

    check = kwargs.pop('check', None) or AgentCheck('test', {}, [{}])
    check.check_id = 'test:instance'

    return QueryManager(check, executor, args, **kwargs)
