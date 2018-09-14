# (C) Datadog, Inc. 2013-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# datadog
from datadog_checks.checks.win import PDHBaseCheck

DEFAULT_COUNTERS = [
    # counterset, instance of counter, counter name, metric name
    # This set is from the Microsoft recommended counters to monitor exchange:
    # https://technet.microsoft.com/en-us/library/dn904093%28v=exchg.150%29.aspx?f=255&MSPPError=-2147217396
    # Exchange Domain Controller Connectivity Counters
    ["MSExchange ADAccess Domain Controllers", None, "LDAP Read Time",   "exchange.adaccess_domain_controllers.ldap_read",   "gauge"],  # noqa: E501
    ["MSExchange ADAccess Domain Controllers", None, "LDAP Search Time", "exchange.adaccess_domain_controllers.ldap_search", "gauge"],  # noqa: E501
    ["MSExchange ADAccess Processes",          None, "LDAP Read Time",   "exchange.adaccess_processes.ldap_read",            "gauge"],  # noqa: E501
    ["MSExchange ADAccess Processes",          None, "LDAP Search Time", "exchange.adaccess_processes.ldap_search",          "gauge"],  # noqa: E501
    # Processor and Process Counters
    ["Processor", "_Total", "% Processor Time",       "exchange.processor.cpu_time",       "gauge"],  # noqa: E501
    ["Processor", "_Total", "% User Time",            "exchange.processor.cpu_user",       "gauge"],  # noqa: E501
    ["Processor", "_Total", "% Privileged Time",      "exchange.processor.cpu_privileged", "gauge"],  # noqa: E501
    ["System",    None,     "Processor Queue Length", "exchange.processor.queue_length",   "gauge"],  # noqa: E501
    # Memory Counters
    ["Memory", None, "Available MBytes",         "exchange.memory.available", "gauge"],  # noqa: E501
    ["Memory", None, "% Committed Bytes In Use", "exchange.memory.committed", "gauge"],  # noqa: E501
    # Network Counters
    ["Network Interface", None, "Packets Outbound Errors", "exchange.network.outbound_errors",           "gauge"],  # noqa: E501
    ["TCPv6",             None, "Connection Failures",     "exchange.network.tcpv6.connection_failures", "gauge"],  # noqa: E501
    ["TCPv4",             None, "Connections Reset",       "exchange.network.tcpv4.conns_reset",         "count"],  # noqa: E501
    ["TCPv6",             None, "Connections Reset",       "exchange.network.tcpv6.conns_reset",         "count"],  # noqa: E501
    # Netlogon Counters
    ["Netlogon", None, "Semaphore Waiters",           "exchange.netlogon.semaphore_waiters",   "gauge"],  # noqa: E501
    ["Netlogon", None, "Semaphore Holders",           "exchange.netlogon.semaphore_holders",   "gauge"],  # noqa: E501
    ["Netlogon", None, "Semaphore Acquires",          "exchange.netlogon.semaphore_acquires",  "count"],  # noqa: E501
    ["Netlogon", None, "Semaphore Timeouts",          "exchange.netlogon.semaphore_timeouts",  "count"],  # noqa: E501
    ["Netlogon", None, "Average Semaphore Hold Time", "exchange.netlogon.semaphore_hold_time", "gauge"],  # noqa: E501

    # Database counters
    ["MSExchange Database ==> Instances", None,     "I/O Database Reads (Attached) Average Latency",  "exchange.database.io_reads_avg_latency",              "gauge"],  # noqa: E501
    ["MSExchange Database ==> Instances", None,     "I/O Database Writes (Attached) Average Latency", "exchange.database.io_writes_avg_latency",             "gauge"],  # noqa: E501
    ["MSExchange Database ==> Instances", None,     "I/O Log Writes Average Latency",                 "exchange.database.io_log_writes_avg_latency",         "gauge"],  # noqa: E501
    ["MSExchange Database ==> Instances", None,     "I/O Database Reads (Recovery) Average Latency",  "exchange.database.io_db_reads_recovery_avg_latency",  "gauge"],  # noqa: E501
    ["MSExchange Database ==> Instances", None,     "I/O Database Writes (Recovery) Average Latency", "exchange.database.io_db_writes_recovery_avg_latency", "gauge"],  # noqa: E501
    ["MSExchange Database ==> Instances", None,     "I/O Database Reads (Attached)/sec",              "exchange.database.io_db_reads_attached_persec",       "gauge"],  # noqa: E501
    ["MSExchange Database ==> Instances", None,     "I/O Database Writes (Attached)/sec",             "exchange.database.io_db_writes_attached_persec",      "gauge"],  # noqa: E501
    ["MSExchange Database ==> Instances", None,     "I/O Log Writes/sec",                             "exchange.database.io_log_writes_persec",              "gauge"],  # noqa: E501
    ["MSExchange Active Manager",         "_total", "Database Mounted",                               "exchange.activemanager.database_mounted",             "gauge"],  # noqa: E501

    # RPC Client Access Counters
    ["MSExchange RpcClientAccess", None, "RPC Averaged Latency", "exchange.rpc.averaged_latency",  "gauge"],  # noqa: E501
    ["MSExchange RpcClientAccess", None, "RPC Requests",         "exchange.rpc.requests",          "gauge"],  # noqa: E501
    ["MSExchange RpcClientAccess", None, "Active User Count",    "exchange.rpc.active_user_count", "gauge"],  # noqa: E501
    ["MSExchange RpcClientAccess", None, "Connection Count",     "exchange.rpc.conn_count",        "gauge"],  # noqa: E501
    ["MSExchange RpcClientAccess", None, "RPC Operations/sec",   "exchange.rpc.ops_persec",        "gauge"],  # noqa: E501
    ["MSExchange RpcClientAccess", None, "User Count",           "exchange.rpc.user_count",        "gauge"],  # noqa: E501

    # HTTP Proxy Counters
    ["MSExchange HttpProxy", None, "MailboxServerLocator Average Latency",           "exchange.httpproxy.server_locator_latency",          "gauge"],  # noqa: E501
    ["MSExchange HttpProxy", None, "Average Authentication Latency",                 "exchange.httpproxy.avg_auth_latency",                "gauge"],  # noqa: E501
    ["MSExchange HttpProxy", None, "Average ClientAccess Server Processing Latency", "exchange.httpproxy.clientaccess_processing_latency", "gauge"],  # noqa: E501
    ["MSExchange HttpProxy", None, "Mailbox Server Proxy Failure Rate",              "exchange.httpproxy.mailbox_proxy_failure_rate",      "gauge"],  # noqa: E501
    ["MSExchange HttpProxy", None, "Outstanding Proxy Requests",                     "exchange.httpproxy.outstanding_requests",            "gauge"],  # noqa: E501
    ["MSExchange HttpProxy", None, "Proxy Requests/Sec",                             "exchange.httpproxy.proxy_requests_persec",           "gauge"],  # noqa: E501
    ["MSExchange HttpProxy", None, "Requests/Sec",                                   "exchange.httpproxy.requests_persec",                 "gauge"],  # noqa: E501

    # Information Store Counters
    ["MSExchangeIS Store",       None, "RPC Requests",        "exchange.is.store.rpc_requests",        "gauge"],  # noqa: E501
    ["MSExchangeIS Client Type", None, "RPC Average Latency", "exchange.is.clienttype.rpc_latency",    "gauge"],  # noqa: E501
    ["MSExchangeIS Store",       None, "RPC Average Latency", "exchange.is.store.rpc_latency",         "gauge"],  # noqa: E501
    ["MSExchangeIS Store",       None, "RPC Operations/sec",  "exchange.is.store.rpc_ops_persec",      "gauge"],  # noqa: E501
    ["MSExchangeIS Client Type", None, "RPC Operations/sec",  "exchange.is.clienttype.rpc_ops_persec", "gauge"],  # noqa: E501

    # Client Access Server Counters
    ["MSExchange ActiveSync",  None,     "Requests/sec",              "exchange.activesync.requests_persec",             "gauge"],  # noqa: E501
    ["MSExchange ActiveSync",  None,     "Ping Commands Pending",     "exchange.activesync.ping_pending",                "gauge"],  # noqa: E501
    ["MSExchange ActiveSync",  None,     "Sync Commands/sec",         "exchange.activesync.sync_persec",                 "gauge"],  # noqa: E501
    ["MSExchange OWA",         None,     "Current Unique Users",      "exchange.owa.unique_users",                       "gauge"],  # noqa: E501
    ["MSExchange OWA",         None,     "Requests/sec",              "exchange.owa.requests_persec",                    "gauge"],  # noqa: E501
    ["MSExchangeAutodiscover", None,     "Requests/sec",              "exchange.autodiscover.requests_persec",           "gauge"],  # noqa: E501
    ["MSExchangeWS",           None,     "Requests/sec",              "exchange.ws.requests_persec",                     "gauge"],  # noqa: E501
    ["Web Service",            "_Total", "Current Connections",       "exchange.ws.current_connections_total",           "gauge"],  # noqa: E501
    ["Web Service",            None,     "Current Connections",       "exchange.ws.current_connections_default_website", "gauge"],  # noqa: E501
    ["Web Service",            "_Total", "Connection Attempts/sec",   "exchange.ws.connection_attempts",                 "gauge"],  # noqa: E501
    ["Web Service",            "_Total", "Other Request Methods/sec", "exchange.ws.other_attempts",                      "gauge"],  # noqa: E501

    # Workload Management Counters
    ["MSExchange WorkloadManagement Workloads", None, "ActiveTasks",    "exchange.workload_management.active_tasks",    "gauge"],  # noqa: E501
    ["MSExchange WorkloadManagement Workloads", None, "CompletedTasks", "exchange.workload_management.completed_tasks", "gauge"],  # noqa: E501
    ["MSExchange WorkloadManagement Workloads", None, "QueuedTasks",    "exchange.workload_management.queued_tasks",    "gauge"],  # noqa: E501

]


class ExchangeCheck(PDHBaseCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        PDHBaseCheck.__init__(self, name, init_config, agentConfig, instances=instances, counter_list=DEFAULT_COUNTERS)
