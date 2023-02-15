# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import AgentCheck

RATE = AgentCheck.rate
GAUGE = AgentCheck.gauge

CONFIG_METRICS = {
    'descriptors': [],
    'metrics': [
        ('max_client_conn', ('pgbouncer.max_client_conn', GAUGE)),
    ],
    'query': """SHOW CONFIG""",
}

STATS_METRICS = {
    'descriptors': [('database', 'db'), ('database', 'pgbouncer_db')],
    'metrics': [
        ('total_requests', ('pgbouncer.stats.requests_per_second', RATE)),  # < 1.8
        ('total_xact_count', ('pgbouncer.stats.transactions_per_second', RATE)),  # >= 1.8
        ('total_query_count', ('pgbouncer.stats.queries_per_second', RATE)),  # >= 1.8
        ('total_received', ('pgbouncer.stats.bytes_received_per_second', RATE)),
        ('total_sent', ('pgbouncer.stats.bytes_sent_per_second', RATE)),
        ('total_query_time', ('pgbouncer.stats.total_query_time', RATE)),
        ('total_xact_time', ('pgbouncer.stats.total_transaction_time', RATE)),  # >= 1.8
        ('total_wait_time', ('pgbouncer.stats.total_wait_time', RATE)),  # >= 1.8
        ('avg_req', ('pgbouncer.stats.avg_req', GAUGE)),  # < 1.8
        ('avg_xact_count', ('pgbouncer.stats.avg_transaction_count', GAUGE)),  # >= 1.8
        ('avg_query_count', ('pgbouncer.stats.avg_query_count', GAUGE)),  # >= 1.8
        ('avg_wait_time', ('pgbouncer.stats.avg_wait_time', GAUGE)),  # >= 1.8
        ('avg_recv', ('pgbouncer.stats.avg_recv', GAUGE)),
        ('avg_sent', ('pgbouncer.stats.avg_sent', GAUGE)),
        ('avg_query', ('pgbouncer.stats.avg_query', GAUGE)),  # < 1.8
        ('avg_xact_time', ('pgbouncer.stats.avg_transaction_time', GAUGE)),  # >= 1.8
        ('avg_query_time', ('pgbouncer.stats.avg_query_time', GAUGE)),  # >= 1.8
    ],
    'query': """SHOW STATS""",
}

POOLS_METRICS = {
    'descriptors': [('database', 'db'), ('database', 'pgbouncer_db'), ('user', 'user')],
    'metrics': [
        ('cl_active', ('pgbouncer.pools.cl_active', GAUGE)),
        ('cl_waiting', ('pgbouncer.pools.cl_waiting', GAUGE)),
        ('sv_active', ('pgbouncer.pools.sv_active', GAUGE)),
        ('sv_idle', ('pgbouncer.pools.sv_idle', GAUGE)),
        ('sv_used', ('pgbouncer.pools.sv_used', GAUGE)),
        ('sv_tested', ('pgbouncer.pools.sv_tested', GAUGE)),
        ('sv_login', ('pgbouncer.pools.sv_login', GAUGE)),
        ('maxwait', ('pgbouncer.pools.maxwait', GAUGE)),
        ('maxwait_us', ('pgbouncer.pools.maxwait_us', GAUGE)),  # >= 1.8
    ],
    'query': """SHOW POOLS""",
}

DATABASES_METRICS = {
    'descriptors': [('name', 'name'), ('name', 'pgbouncer_db')],
    'metrics': [
        ('pool_size', ('pgbouncer.databases.pool_size', GAUGE)),
        ('max_connections', ('pgbouncer.databases.max_connections', GAUGE)),
        ('current_connections', ('pgbouncer.databases.current_connections', GAUGE)),
    ],
    'query': """SHOW DATABASES""",
}

CLIENTS_METRICS = {
    'descriptors': [('database', 'db'), ('database', 'pgbouncer_db'), ('user', 'user'), ('state', 'state')],
    'metrics': [
        ('connect_time', ('pgbouncer.clients.connect_time', GAUGE)),
        ('request_time', ('pgbouncer.clients.request_time', GAUGE)),
        ('wait', ('pgbouncer.clients.wait', GAUGE)),  # >= 1.8
        ('wait_us', ('pgbouncer.clients.wait_us', GAUGE)),  # >= 1.8
    ],
    'query': """SHOW CLIENTS""",
}

SERVERS_METRICS = {
    'descriptors': [('database', 'db'), ('database', 'pgbouncer_db'), ('user', 'user'), ('state', 'state')],
    'metrics': [
        ('connect_time', ('pgbouncer.servers.connect_time', GAUGE)),
        ('request_time', ('pgbouncer.servers.request_time', GAUGE)),
    ],
    'query': """SHOW SERVERS""",
}
