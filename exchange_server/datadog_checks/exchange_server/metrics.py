# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRICS_CONFIG = {
    'MSExchange ADAccess Domain Controllers': {
        'name': 'adaccess_domain_controllers',
        'counters': [
            {
                'LDAP Read Time': 'ldap_read',
                'LDAP Search Time': 'ldap_search',
            }
        ],
    },
    'MSExchange ADAccess Processes': {
        'name': 'adaccess_processes',
        'counters': [
            {
                'LDAP Read Time': 'ldap_read',
                'LDAP Search Time': 'ldap_search',
            }
        ],
    },
    'Processor': {
        'name': 'processor',
        'counters': [
            {
                '% Processor Time': {'name': 'cpu_time', 'aggregate': 'only'},
                '% User Time': {'name': 'cpu_user', 'aggregate': 'only'},
                '% Privileged Time': {'name': 'cpu_privileged', 'aggregate': 'only'},
            }
        ],
    },
    'System': {
        'name': 'processor',
        'counters': [
            {
                'Processor Queue Length': 'queue_length',
            }
        ],
    },
    'Memory': {
        'name': 'memory',
        'counters': [
            {
                'Available MBytes': 'available',
                '% Committed Bytes In Use': 'committed',
            }
        ],
    },
    'Network Interface': {
        'name': 'network',
        'counters': [
            {
                'Packets Outbound Errors': 'outbound_errors',
            }
        ],
    },
    'TCPv6': {
        'name': 'network.tcpv6',
        'counters': [
            {
                'Connection Failures': 'connection_failures',
                'Connections Reset': {'name': 'conns_reset', 'type': 'count'},
            }
        ],
    },
    'TCPv4': {
        'name': 'network.tcpv4',
        'counters': [
            {
                'Connections Reset': {'name': 'conns_reset', 'type': 'count'},
            }
        ],
    },
    'Netlogon': {
        'name': 'netlogon',
        'counters': [
            {
                'Semaphore Waiters': 'semaphore_waiters',
                'Semaphore Holders': 'semaphore_holders',
                'Semaphore Acquires': {'name': 'semaphore_acquires', 'type': 'count'},
                'Semaphore Timeouts': {'name': 'semaphore_timeouts', 'type': 'count'},
                'Average Semaphore Hold Time': 'semaphore_hold_time',
            }
        ],
    },
    'MSExchange Database ==> Instances': {
        'name': 'database',
        'counters': [
            {
                'I/O Database Reads (Attached) Average Latency': 'io_reads_avg_latency',
                'I/O Database Writes (Attached) Average Latency': 'io_writes_avg_latency',
                'I/O Log Writes Average Latency': 'io_log_writes_avg_latency',
                'I/O Database Reads (Recovery) Average Latency': 'io_db_reads_recovery_avg_latency',
                'I/O Database Writes (Recovery) Average Latency': 'io_db_writes_recovery_avg_latency',
                'I/O Database Reads (Attached)/sec': 'io_db_reads_attached_persec',
                'I/O Database Writes (Attached)/sec': 'io_db_writes_attached_persec',
                'I/O Log Writes/sec': 'io_log_writes_persec',
            }
        ],
    },
    'MSExchange Active Manager': {
        'name': 'activemanager',
        'counters': [
            {
                'Database Mounted': {'name': 'database_mounted', 'aggregate': 'only'},
            }
        ],
    },
    'MSExchange RpcClientAccess': {
        'name': 'rpc',
        'counters': [
            {
                'RPC Averaged Latency': 'averaged_latency',
                'RPC Requests': 'requests',
                'Active User Count': 'active_user_count',
                'Connection Count': 'conn_count',
                'RPC Operations/sec': 'ops_persec',
                'User Count': 'user_count',
            }
        ],
    },
    'MSExchange HttpProxy': {
        'name': 'httpproxy',
        'counters': [
            {
                'MailboxServerLocator Average Latency': 'server_locator_latency',
                'Average Authentication Latency': 'avg_auth_latency',
                'Average ClientAccess Server Processing Latency': 'clientaccess_processing_latency',
                'Mailbox Server Proxy Failure Rate': 'mailbox_proxy_failure_rate',
                'Outstanding Proxy Requests': 'outstanding_requests',
                'Proxy Requests/Sec': 'proxy_requests_persec',
                'Requests/Sec': 'requests_persec',
            }
        ],
    },
    'MSExchangeIS Store': {
        'name': 'is.store',
        'counters': [
            {
                'RPC Requests': 'rpc_requests',
                'RPC Average Latency': 'rpc_latency',
                'RPC Operations/sec': 'rpc_ops_persec',
            }
        ],
    },
    'MSExchangeIS Client Type': {
        'name': 'is.clienttype',
        'counters': [
            {
                'RPC Average Latency': 'rpc_latency',
                'RPC Operations/sec': 'rpc_ops_persec',
            }
        ],
    },
    'MSExchange ActiveSync': {
        'name': 'activesync',
        'counters': [
            {
                'Requests/sec': 'requests_persec',
                'Ping Commands Pending': 'ping_pending',
                'Sync Commands/sec': 'sync_persec',
            }
        ],
    },
    'MSExchange OWA': {
        'name': 'owa',
        'counters': [
            {
                'Current Unique Users': 'unique_users',
                'Requests/sec': 'requests_persec',
            }
        ],
    },
    'MSExchangeAutodiscover': {
        'name': 'autodiscover',
        'counters': [
            {
                'Requests/sec': 'requests_persec',
            }
        ],
    },
    'MSExchangeWS': {
        'name': 'ws',
        'counters': [
            {
                'Requests/sec': 'requests_persec',
            }
        ],
    },
    'Web Service': {
        'name': 'ws',
        'counters': [
            {
                'Current Connections': {'name': 'current_connections_default_website', 'aggregate': True},
                'Connection Attempts/sec': {'name': 'connection_attempts', 'aggregate': 'only'},
                'Other Request Methods/sec': {'name': 'other_attempts', 'aggregate': 'only'},
            }
        ],
    },
    'MSExchange WorkloadManagement Workloads': {
        'name': 'workload_management',
        'counters': [
            {
                'ActiveTasks': 'active_tasks',
                'CompletedTasks': 'completed_tasks',
                'QueuedTasks': 'queued_tasks',
            }
        ],
    },
}

DEFAULT_COUNTERS = [
    # counterset, instance of counter, counter name, metric name
    # This set is from the Microsoft recommended counters to monitor exchange:
    # https://technet.microsoft.com/en-us/library/dn904093%28v=exchg.150%29.aspx?f=255&MSPPError=-2147217396
    # Exchange Domain Controller Connectivity Counters
    [
        'MSExchange ADAccess Domain Controllers',
        None,
        'LDAP Read Time',
        'exchange.adaccess_domain_controllers.ldap_read',
        'gauge',
    ],
    [
        'MSExchange ADAccess Domain Controllers',
        None,
        'LDAP Search Time',
        'exchange.adaccess_domain_controllers.ldap_search',
        'gauge',
    ],
    ['MSExchange ADAccess Processes', None, 'LDAP Read Time', 'exchange.adaccess_processes.ldap_read', 'gauge'],
    ['MSExchange ADAccess Processes', None, 'LDAP Search Time', 'exchange.adaccess_processes.ldap_search', 'gauge'],
    # Processor and Process Counters
    ['Processor', '_Total', '% Processor Time', 'exchange.processor.cpu_time', 'gauge'],
    ['Processor', '_Total', '% User Time', 'exchange.processor.cpu_user', 'gauge'],
    ['Processor', '_Total', '% Privileged Time', 'exchange.processor.cpu_privileged', 'gauge'],
    ['System', None, 'Processor Queue Length', 'exchange.processor.queue_length', 'gauge'],
    # Memory Counters
    ['Memory', None, 'Available MBytes', 'exchange.memory.available', 'gauge'],
    ['Memory', None, '% Committed Bytes In Use', 'exchange.memory.committed', 'gauge'],
    # Network Counters
    ['Network Interface', None, 'Packets Outbound Errors', 'exchange.network.outbound_errors', 'gauge'],
    ['TCPv6', None, 'Connection Failures', 'exchange.network.tcpv6.connection_failures', 'gauge'],
    ['TCPv4', None, 'Connections Reset', 'exchange.network.tcpv4.conns_reset', 'count'],
    ['TCPv6', None, 'Connections Reset', 'exchange.network.tcpv6.conns_reset', 'count'],
    # Netlogon Counters
    ['Netlogon', None, 'Semaphore Waiters', 'exchange.netlogon.semaphore_waiters', 'gauge'],
    ['Netlogon', None, 'Semaphore Holders', 'exchange.netlogon.semaphore_holders', 'gauge'],
    ['Netlogon', None, 'Semaphore Acquires', 'exchange.netlogon.semaphore_acquires', 'count'],
    ['Netlogon', None, 'Semaphore Timeouts', 'exchange.netlogon.semaphore_timeouts', 'count'],
    ['Netlogon', None, 'Average Semaphore Hold Time', 'exchange.netlogon.semaphore_hold_time', 'gauge'],
    # Database counters
    [
        'MSExchange Database ==> Instances',
        None,
        'I/O Database Reads (Attached) Average Latency',
        'exchange.database.io_reads_avg_latency',
        'gauge',
    ],
    [
        'MSExchange Database ==> Instances',
        None,
        'I/O Database Writes (Attached) Average Latency',
        'exchange.database.io_writes_avg_latency',
        'gauge',
    ],
    [
        'MSExchange Database ==> Instances',
        None,
        'I/O Log Writes Average Latency',
        'exchange.database.io_log_writes_avg_latency',
        'gauge',
    ],
    [
        'MSExchange Database ==> Instances',
        None,
        'I/O Database Reads (Recovery) Average Latency',
        'exchange.database.io_db_reads_recovery_avg_latency',
        'gauge',
    ],
    [
        'MSExchange Database ==> Instances',
        None,
        'I/O Database Writes (Recovery) Average Latency',
        'exchange.database.io_db_writes_recovery_avg_latency',
        'gauge',
    ],
    [
        'MSExchange Database ==> Instances',
        None,
        'I/O Database Reads (Attached)/sec',
        'exchange.database.io_db_reads_attached_persec',
        'gauge',
    ],
    [
        'MSExchange Database ==> Instances',
        None,
        'I/O Database Writes (Attached)/sec',
        'exchange.database.io_db_writes_attached_persec',
        'gauge',
    ],
    [
        'MSExchange Database ==> Instances',
        None,
        'I/O Log Writes/sec',
        'exchange.database.io_log_writes_persec',
        'gauge',
    ],
    ['MSExchange Active Manager', '_total', 'Database Mounted', 'exchange.activemanager.database_mounted', 'gauge'],
    # RPC Client Access Counters
    ['MSExchange RpcClientAccess', None, 'RPC Averaged Latency', 'exchange.rpc.averaged_latency', 'gauge'],
    ['MSExchange RpcClientAccess', None, 'RPC Requests', 'exchange.rpc.requests', 'gauge'],
    ['MSExchange RpcClientAccess', None, 'Active User Count', 'exchange.rpc.active_user_count', 'gauge'],
    ['MSExchange RpcClientAccess', None, 'Connection Count', 'exchange.rpc.conn_count', 'gauge'],
    ['MSExchange RpcClientAccess', None, 'RPC Operations/sec', 'exchange.rpc.ops_persec', 'gauge'],
    ['MSExchange RpcClientAccess', None, 'User Count', 'exchange.rpc.user_count', 'gauge'],
    # HTTP Proxy Counters
    [
        'MSExchange HttpProxy',
        None,
        'MailboxServerLocator Average Latency',
        'exchange.httpproxy.server_locator_latency',
        'gauge',
    ],
    ['MSExchange HttpProxy', None, 'Average Authentication Latency', 'exchange.httpproxy.avg_auth_latency', 'gauge'],
    [
        'MSExchange HttpProxy',
        None,
        'Average ClientAccess Server Processing Latency',
        'exchange.httpproxy.clientaccess_processing_latency',
        'gauge',
    ],
    [
        'MSExchange HttpProxy',
        None,
        'Mailbox Server Proxy Failure Rate',
        'exchange.httpproxy.mailbox_proxy_failure_rate',
        'gauge',
    ],
    ['MSExchange HttpProxy', None, 'Outstanding Proxy Requests', 'exchange.httpproxy.outstanding_requests', 'gauge'],
    ['MSExchange HttpProxy', None, 'Proxy Requests/Sec', 'exchange.httpproxy.proxy_requests_persec', 'gauge'],
    ['MSExchange HttpProxy', None, 'Requests/Sec', 'exchange.httpproxy.requests_persec', 'gauge'],
    # Information Store Counters
    ['MSExchangeIS Store', None, 'RPC Requests', 'exchange.is.store.rpc_requests', 'gauge'],
    ['MSExchangeIS Client Type', None, 'RPC Average Latency', 'exchange.is.clienttype.rpc_latency', 'gauge'],
    ['MSExchangeIS Store', None, 'RPC Average Latency', 'exchange.is.store.rpc_latency', 'gauge'],
    ['MSExchangeIS Store', None, 'RPC Operations/sec', 'exchange.is.store.rpc_ops_persec', 'gauge'],
    ['MSExchangeIS Client Type', None, 'RPC Operations/sec', 'exchange.is.clienttype.rpc_ops_persec', 'gauge'],
    # Client Access Server Counters
    ['MSExchange ActiveSync', None, 'Requests/sec', 'exchange.activesync.requests_persec', 'gauge'],
    ['MSExchange ActiveSync', None, 'Ping Commands Pending', 'exchange.activesync.ping_pending', 'gauge'],
    ['MSExchange ActiveSync', None, 'Sync Commands/sec', 'exchange.activesync.sync_persec', 'gauge'],
    ['MSExchange OWA', None, 'Current Unique Users', 'exchange.owa.unique_users', 'gauge'],
    ['MSExchange OWA', None, 'Requests/sec', 'exchange.owa.requests_persec', 'gauge'],
    ['MSExchangeAutodiscover', None, 'Requests/sec', 'exchange.autodiscover.requests_persec', 'gauge'],
    ['MSExchangeWS', None, 'Requests/sec', 'exchange.ws.requests_persec', 'gauge'],
    ['Web Service', '_Total', 'Current Connections', 'exchange.ws.current_connections_total', 'gauge'],
    ['Web Service', None, 'Current Connections', 'exchange.ws.current_connections_default_website', 'gauge'],
    ['Web Service', '_Total', 'Connection Attempts/sec', 'exchange.ws.connection_attempts', 'gauge'],
    ['Web Service', '_Total', 'Other Request Methods/sec', 'exchange.ws.other_attempts', 'gauge'],
    # Workload Management Counters
    [
        'MSExchange WorkloadManagement Workloads',
        None,
        'ActiveTasks',
        'exchange.workload_management.active_tasks',
        'gauge',
    ],
    [
        'MSExchange WorkloadManagement Workloads',
        None,
        'CompletedTasks',
        'exchange.workload_management.completed_tasks',
        'gauge',
    ],
    [
        'MSExchange WorkloadManagement Workloads',
        None,
        'QueuedTasks',
        'exchange.workload_management.queued_tasks',
        'gauge',
    ],
]
