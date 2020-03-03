from datadog_checks.base import AgentCheck

RATE = AgentCheck.rate
GAUGE = AgentCheck.gauge


STATS_METRICS = {
    'descriptors': [('database', 'db')],
    'metrics': [
        ('total_requests', ('pgbouncer.stats.requests_per_second', RATE)),  # < 1.8
        ('total_xact_count', ('pgbouncer.stats.transactions_per_second', RATE)),  # >= 1.8
        ('total_query_count', ('pgbouncer.stats.queries_per_second', RATE)),  # >= 1.8
        ('total_received', ('pgbouncer.stats.bytes_received_per_second', RATE)),
        ('total_sent', ('pgbouncer.stats.bytes_sent_per_second', RATE)),
        ('total_query_time', ('pgbouncer.stats.total_query_time', RATE)),
        ('total_xact_time', ('pgbouncer.stats.total_transaction_time', RATE)),  # >= 1.8
        ('avg_req', ('pgbouncer.stats.avg_req', GAUGE)),  # < 1.8
        ('avg_xact_count', ('pgbouncer.stats.avg_transaction_count', GAUGE)),  # >= 1.8
        ('avg_query_count', ('pgbouncer.stats.avg_query_count', GAUGE)),  # >= 1.8
        ('avg_recv', ('pgbouncer.stats.avg_recv', GAUGE)),
        ('avg_sent', ('pgbouncer.stats.avg_sent', GAUGE)),
        ('avg_query', ('pgbouncer.stats.avg_query', GAUGE)),  # < 1.8
        ('avg_xact_time', ('pgbouncer.stats.avg_transaction_time', GAUGE)),  # >= 1.8
        ('avg_query_time', ('pgbouncer.stats.avg_query_time', GAUGE)),  # >= 1.8
    ],
    'query': """SHOW STATS""",
}

POOLS_METRICS = {
    'descriptors': [('database', 'db'), ('user', 'user')],
    'metrics': [
        ('cl_active', ('pgbouncer.pools.cl_active', GAUGE)),
        ('cl_waiting', ('pgbouncer.pools.cl_waiting', GAUGE)),
        ('sv_active', ('pgbouncer.pools.sv_active', GAUGE)),
        ('sv_idle', ('pgbouncer.pools.sv_idle', GAUGE)),
        ('sv_used', ('pgbouncer.pools.sv_used', GAUGE)),
        ('sv_tested', ('pgbouncer.pools.sv_tested', GAUGE)),
        ('sv_login', ('pgbouncer.pools.sv_login', GAUGE)),
        ('maxwait', ('pgbouncer.pools.maxwait', GAUGE)),
    ],
    'query': """SHOW POOLS""",
}

DATABASES_METRICS = {
    'descriptors': [('name', 'name')],
    'metrics': [
        ('pool_size', ('pgbouncer.databases.pool_size', GAUGE)),
        ('max_connections', ('pgbouncer.databases.max_connections', GAUGE)),
        ('current_connections', ('pgbouncer.databases.current_connections', GAUGE)),
    ],
    'query': """SHOW DATABASES""",
}
