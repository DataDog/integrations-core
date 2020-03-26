# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.utils.db import Query

STATS_MYSQL_GLOBAL = Query(
    {
        'name': 'stats_mysql_global',
        'query': 'SELECT * FROM stats.stats_mysql_global',
        'columns': [
            {
                'name': 'Variable_Name',
                'type': 'match',
                'source': 'Variable_Value',
                'items': {
                    # the total uptime of ProxySQL in seconds
                    'ProxySQL_Uptime': {'name': 'uptime', 'type': 'gauge'},
                    # memory used by the embedded SQLite
                    'SQLite3_memory_bytes': {'name': 'memory.sqlite3_memory_bytes', 'type': 'gauge'},
                    # provides a count of how many client connection are currently processing a transaction
                    'Active_Transactions': {'name': 'active_transactions', 'type': 'gauge'},
                    # client failed connections (or closed improperly)
                    'Client_Connections_aborted': {'name': 'client.connections_aborted', 'type': 'rate'},
                    # client connections that are currently connected
                    'Client_Connections_connected': {'name': 'client.connections_connected', 'type': 'gauge'},
                    # total number of client connections created
                    'Client_Connections_created': {'name': 'client.connections_created', 'type': 'rate'},
                    # backend failed connections (or closed improperly)
                    'Server_Connections_aborted': {'name': 'server.connections_aborted', 'type': 'rate'},
                    # backend connections that are currently connected
                    'Server_Connections_connected': {'name': 'server.connections_connected', 'type': 'gauge'},
                    # total number of backend connections created
                    'Server_Connections_created': {'name': 'server.connections_created', 'type': 'rate'},
                    # number of client connections that are currently handled by the main worker threads. If ProxySQL
                    # isn't running with "--idle-threads", Client_Connections_non_idle is always equal to
                    # "Client_Connections_connected"
                    'Client_Connections_non_idle': {'name': 'client.connections_non_idle', 'type': 'gauge'},
                    # time spent making network calls to communicate with the backends
                    'Backend_query_time_nsec': {
                        'name': 'backend.query_time_pct',
                        'type': 'temporal_percent',
                        'scale': 'nanosecond',
                    },
                    # buffers related to backend connections if "fast_forward" is used, 0 means fast_forward is not used
                    'mysql_backend_buffers_bytes': {'name': 'mysql.backend_buffers_bytes', 'type': 'gauge'},
                    # buffers related to frontend connections (read/write buffers and other queues)
                    'mysql_frontend_buffers_bytes': {'name': 'mysql.frontend_buffers_bytes', 'type': 'gauge'},
                    # other memory used by ProxySQL to handle MySQL Sessions
                    'mysql_session_internal_bytes': {'name': 'mysql.session_internal_bytes', 'type': 'gauge'},
                    # number of MySQL Thread workers i.e. "mysql-threads"
                    'MySQL_Thread_Workers': {'name': 'mysql.thread_workers', 'type': 'gauge'},
                    # The number of monitor threads. By default it is twice the number of worker threads, initially
                    # capped to 16 yet more threads will be created checks are being queued. Monitor threads perform
                    # blocking network operations and do not consume much CPU
                    'MySQL_Monitor_Workers': {'name': 'mysql.monitor_workers', 'type': 'gauge'},
                    # number of requests where a connection was already available in the connection pool
                    'ConnPool_get_conn_success': {'name': 'pool.conn_success', 'type': 'rate'},
                    # number of requests where a connection was not available in the connection pool and either: a new
                    # connection had to be created or no backend was available
                    'ConnPool_get_conn_failure': {'name': 'pool.conn_failure', 'type': 'rate'},
                    # number of connections that a MySQL Thread obtained from its own local connection pool cache.
                    # This value tends to be large only when there is high concurrency.
                    'ConnPool_get_conn_immediate': {'name': 'pool.conn_immediate', 'type': 'rate'},
                    # the total number of client requests / statements executed
                    'Questions': {'name': 'questions', 'type': 'rate'},
                    # the total number of queries with an execution time greater than mysql-long_query_time milliseconds
                    'Slow_queries': {'name': 'slow_queries', 'type': 'rate'},
                    # memory used by the connection pool to store connections metadata
                    'ConnPool_memory_bytes': {'name': 'pool.memory_bytes', 'type': 'gauge'},
                    # the total number of prepared statements that are in use by clients
                    'Stmt_Client_Active_Total': {'name': 'client.statements.active_total', 'type': 'gauge'},
                    # this variable tracks the number of unique prepared statements currently in use by clients
                    'Stmt_Client_Active_Unique': {'name': 'client.statements.active_unique', 'type': 'gauge'},
                    # the total number of prepared statements currently available across all backend connections
                    'Stmt_Server_Active_Total': {'name': 'server.statements.active_total', 'type': 'gauge'},
                    # the number of unique prepared statements currently available across all backend connections
                    'Stmt_Server_Active_Unique': {'name': 'server.statements.active_unique', 'type': 'gauge'},
                    # this is the number of global prepared statements for which proxysql has metadata
                    'Stmt_Cached': {'name': 'statements.cached', 'type': 'gauge'},
                    # memory currently used by the query cache
                    'Query_Cache_Memory_bytes': {'name': 'query_cache.memory_bytes', 'type': 'gauge'},
                    # number of entries currently stored in the query cache
                    'Query_Cache_Entries': {'name': 'query_cache.entries', 'type': 'gauge'},
                    # number of entries purged by the Query Cache due to TTL expiration
                    'Query_Cache_Purged': {'name': 'query_cache.purged', 'type': 'rate'},
                    # TODO: Are the following cache metrics monotonic counters?
                    # number of bytes sent into the Query Cache
                    'Query_Cache_bytes_IN': {'name': 'query_cache.bytes_in', 'type': 'gauge'},
                    # number of bytes read from the Query Cache
                    'Query_Cache_bytes_OUT': {'name': 'query_cache.bytes_out', 'type': 'gauge'},
                    # number of read requests
                    'Query_Cache_count_GET': {'name': 'query_cache.get.count', 'type': 'gauge'},
                    # number of successful read requests
                    'Query_Cache_count_GET_OK': {'name': 'query_cache.get_ok.count', 'type': 'gauge'},
                    # number of write requests
                    'Query_Cache_count_SET': {'name': 'query_cache.set.count', 'type': 'gauge'},
                    # the time spent inside the Query Processor to determine what action needs to be taken with the
                    # query (internal module)
                    'Query_Processor_time_nsec': {
                        'name': 'query_processor_time_pct',
                        'type': 'temporal_percent',
                        'scale': 'nanosecond',
                    },
                },
            },
            {'name': 'Variable_Value', 'type': 'source'},
        ],
    }
)

STATS_COMMAND_COUNTERS = Query(
    {
        'name': 'stats_mysql_commands_counters',
        'query': 'SELECT Command, Total_time_us, Total_cnt, cnt_100us, cnt_500us, cnt_1ms, cnt_5ms, cnt_10ms, '
        'cnt_50ms, cnt_100ms, cnt_500ms, cnt_1s, cnt_5s, cnt_10s, cnt_INFs FROM '
        'stats.stats_mysql_commands_counters',
        'columns': [
            # the type of SQL command that has been executed. Examples: FLUSH, INSERT, KILL, SELECT FOR UPDATE, etc.
            {'name': 'sql_command', 'type': 'tag'},
            # the total time spent executing commands of that type, in microseconds
            {'name': 'performance.command.total_time_pct', 'type': 'temporal_percent', 'scale': 'microsecond'},
            # the total number of commands of that type executed
            {'name': 'performance.command.total_count', 'type': 'monotonic_count'},
            # the total number of commands of the given type which executed within the specified time limit and the
            # previous one. For example, cnt_500us is the number of commands which executed within 500 microseconds,
            # but more than 100 microseconds (because there's also a cnt_100us field). cnt_INFs is the number of
            # commands whose execution exceeded 10 seconds.
            {'name': 'performance.command.cnt_100us', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_500us', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_1ms', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_5ms', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_10ms', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_50ms', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_100ms', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_500ms', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_1s', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_5s', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_10s', 'type': 'monotonic_count'},
            {'name': 'performance.command.cnt_infs', 'type': 'monotonic_count'},
        ],
    }
)

STATS_MYSQL_CONNECTION_POOL = Query(
    {
        'name': 'stats_mysql_connection_pool',
        # Need explicit selections as some columns are unusable.
        'query': 'SELECT hostgroup, srv_host, srv_port, status, ConnUsed, ConnFree, ConnOK, ConnERR, Queries, '
        'Bytes_data_sent, Bytes_data_recv, Latency_us FROM stats.stats_mysql_connection_pool',
        'columns': [
            # the hostgroup in which the backend server belongs. Note that a single backend server can belong to more
            # than one hostgroup
            {'name': 'hostgroup', 'type': 'tag'},
            # the TCP endpoint on which the mysqld backend server is listening for connections
            {'name': 'srv_host', 'type': 'tag'},
            {'name': 'srv_port', 'type': 'tag'},
            # the status of the backend server. Can be ONLINE, SHUNNED, OFFLINE_SOFT, OFFLINE_HARD
            # see https://github.com/sysown/proxysql/wiki/Main-(runtime)#mysql_servers
            {
                'name': 'backend.status',
                'type': 'service_check',
                'status_map': {
                    'ONLINE': 'OK',
                    'SHUNNED': 'CRITICAL',
                    'OFFLINE_SOFT': 'WARNING',
                    'OFFLINE_HARD': 'CRITICAL',
                },
            },
            # how many connections are currently used by ProxySQL for sending queries to the backend server
            {'name': 'pool.connections_used', 'type': 'gauge'},
            # how many connections are currently free. They are kept open in order to minimize the time cost of sending
            # a query to the backend server
            {'name': 'pool.connections_free', 'type': 'gauge'},
            # how many connections were established successfully.
            {'name': 'pool.connections_ok', 'type': 'rate'},
            # how many connections weren't established successfully.
            {'name': 'pool.connections_error', 'type': 'rate'},
            # the number of queries routed towards this particular backend server
            {'name': 'pool.queries', 'type': 'rate'},
            # the amount of data sent to the backend. This does not include metadata (packets' headers)
            {'name': 'pool.bytes_data_sent', 'type': 'rate'},
            # the amount of data received from the backend. This does not include metadata (packets' headers,
            # OK/ERR packets, fields' description, etc)
            {'name': 'pool.bytes_data_recv', 'type': 'rate'},
            # the currently ping time in microseconds, as reported from Monitor
            {'name': 'pool.latency_ms', 'type': 'gauge'},
        ],
    }
)

STATS_MYSQL_USERS = Query(
    {
        'name': 'stats_mysql_users',
        'query': 'SELECT username, frontend_connections, frontend_max_connections FROM stats.stats_mysql_users',
        'columns': [
            {'name': 'username', 'type': 'tag'},
            {'name': 'frontend.user_connections', 'type': 'gauge'},
            {'name': 'frontend.user_max_connections', 'type': 'gauge'},
        ],
    }
)

STATS_MEMORY_METRICS = Query(
    {
        'name': 'stats_memory_metrics',
        'query': 'SELECT * FROM stats.stats_memory_metrics',
        'columns': [
            {
                'name': 'Variable_Name',
                'type': 'match',
                'source': 'Variable_Value',
                'items': {
                    # bytes in physically resident data pages mapped by the allocator
                    'jemalloc_resident': {'name': 'memory.jemalloc_resident', 'type': 'gauge'},
                    # bytes in pages allocated by the application
                    'jemalloc_active': {'name': 'memory.jemalloc_active', 'type': 'gauge'},
                    # bytes allocated by the application
                    'jemalloc_allocated': {'name': 'memory.jemalloc_allocated', 'type': 'gauge'},
                    # bytes in extents mapped by the allocator
                    'jemalloc_mapped': {'name': 'memory.jemalloc_mapped', 'type': 'gauge'},
                    # bytes dedicated to metadata
                    'jemalloc_metadata': {'name': 'memory.jemalloc_metadata', 'type': 'gauge'},
                    # bytes in virtual memory mappings that were retained rather than being returned to the OS
                    # http://jemalloc.net/jemalloc.3.html
                    'jemalloc_retained': {'name': 'memory.jemalloc_retained', 'type': 'gauge'},
                    # memory used by the authentication module to store user credentials and attributes
                    'Auth_memory': {'name': 'memory.auth_memory', 'type': 'gauge'},
                    # memory used to store data related to `stats_mysql_query_digest`
                    'query_digest_memory': {'name': 'memory.query_digest_memory', 'type': 'gauge'},
                    # Memory used by the stack of the MySQL threads
                    'stack_memory_mysql_threads': {'name': 'memory.stack_memory_mysql_threads', 'type': 'gauge'},
                    # Memory used by the stack of the admin threads
                    'stack_memory_admin_threads': {'name': 'memory.stack_memory_admin_threads', 'type': 'gauge'},
                    # Memory used by the stack of the cluster threads
                    'stack_memory_cluster_threads': {'name': 'memory.stack_memory_cluster_threads', 'type': 'gauge'},
                },
            },
            {'name': 'Variable_Value', 'type': 'source'},
        ],
    }
)

STATS_MYSQL_QUERY_RULES = Query(
    {
        'name': 'stats_mysql_query_rules',
        'query': 'SELECT rule_id, hits FROM stats.stats_mysql_query_rules',
        'columns': [{'name': 'rule_id', 'type': 'tag'}, {'name': 'query_rules.rule_hits', 'type': 'rate'}],
    }
)
