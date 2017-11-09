# (C) Datadog, Inc. 2013-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# project
from checks import AgentCheck
from utils.containers import hash_mutable
# datadog
try:
    from checks.libs.win.winpdh import WinPDHCounter
except ImportError:
    def WinPDHCounter(*args, **kwargs):
        return


DEFAULT_COUNTERS = [
    # counterset, counter name, metric name
    # This set is from the Microsoft recommended counters to monitor exchange:
    # https://technet.microsoft.com/en-us/library/dn904093%28v=exchg.150%29.aspx?f=255&MSPPError=-2147217396
    # Exchange Domain Controller Connectivity Counters
    ["MSExchange ADAccess Domain Controllers", None, "LDAP Read Time", "exchange.adaccess_domain_controllers.ldap_read", "gauge"],
    ["MSExchange ADAccess Domain Controllers", None, "LDAP Search Time", "exchange.adaccess_domain_controllers.ldap_search", "gauge"],
    ["MSExchange ADAccess Processes", None, "LDAP Read Time", "exchange.adaccess_processes.ldap_read", "gauge"],
    ["MSExchange ADAccess Processes", None, "LDAP Search Time", "exchange.adaccess_processes.ldap_search", "gauge"],
    # Processor and Process Counters
    ["Processor", "_Total", "% Processor Time", "exchange.processor.cpu_time", "gauge"],
    ["Processor", "_Total", "% User Time", "exchange.processor.cpu_user", "gauge"],
    ["Processor", "_Total", "% Privileged Time", "exchange.processor.cpu_privileged", "gauge"],
    ["System", None, "Processor Queue Length", "exchange.processor.queue_length", "gauge"],
    # Memory Counters
    ["Memory", None, "Available Mbytes", "exchange.memory.available", "gauge"],
    ["Memory", None, "% Committed Bytes In Use", "exchange.memory.committed", "gauge"]
    # .NET Framework counters
    [".NET CLR Memory", None, "% Time in GC", "exchange.dotnet_clr_mem.time_in_gc", "gauge"],
    [".NET CLR Exceptions", None, "# of Exceps Thrown / sec", "exchange.dotnet_clr_exceptions.thrown_persec", "gauge"],
    [".NET CLR Memory", None, "# Bytes in all Heaps", "exchange.dotnet_clr_memory.heap_bytes", "gauge"],
    # Network Counters
    ["Network Interface", None, "Packets Outbound Errors", "exchange.network.outbound_errors", "gauge"],
    ["TCPv6", None, "Connection Failures", "exchange.network.tcpv6.connection_failures", "gauge"],
    ["TCPv4", None, "Connections Reset", "exchange.network.tcpv4.conns_reset", "count"],
    ["TCPv6", None, "Connections Reset", "exchange.network.tcpv6.conns_reset", "count"],
    # Netlogon Counters
    ["Netlogon", None, "Semaphore Waiters", "exchange.netlogon.semaphore_waiters", "gauge"],
    ["Netlogon", None, "Semaphore Holders", "exchange.netlogon.semaphore_holders", "gauge"],
    ["Netlogon", None, "Semaphore Acquires", "exchange.netlogon.semaphore_acquires", "count"],
    ["Netlogon", None, "Semaphonre Timeouts", "exchange.netlogon.semaphore_timeouts", "count"],
    ["Netlogon", None, "Average Semaphore Hold Time", "exchange.netlogon.semaphore_hold_time", "gauge"],

    # Database counters
    ["MSExchange Database ==> Instances", None, "I/O Database Reads (Attached) Average Latency", "exchange.database.io_reads_avg_latency", "gauge"],
    ["MSExchange Database ==> Instances", None, "I/O Database Writes (Attached) Average Latency", "exchange.database.io_writes_avg_latency", "gauge"],
    ["MSExchange Database ==> Instances", None, "I/O Log Writes Average Latency", "exchange.database.io_log_writes_avg_latency", "gauge"],
    ["MSExchange Database ==> Instances", None, "I/O Database Reads (Recovery) Average Latency", "exchange.database.io_db_reads_recovery_avg_latency", "gauge"],
    ["MSExchange Database ==> Instances", None, "I/O Database Writes (Recovery) Average Latency", "exchange.database.io_db_writes_recovery_avg_latency", "gauge"],
    ["MSExchange Database ==> Instances", None, "I/O Database Reads (Attached)/sec", "exchange.database.io_db_reads_attached_persec", "gauge"],
    ["MSExchange Database ==> Instances", None, "I/O Database Writes (Attached)/sec", "exchange.database.io_db_writes_attached_persec", "gauge"],
    ["MSExchange Database ==> Instances", None, "I/O Log Writes/sec", "exchange.database.io_log_writes_persec", "gauge"],
    ["MSExchange Active Manager", "_total", "Database Mounted", "exchange.activemanager.database_mounted", "gauge"],

    # ASP.Net
    ["ASP.NET", None, "Application Restarts", "exchange.asp_net.application_restarts", "gauge"],
    ["ASP.NET", None, "Worker Process Restarts", "exchange.asp_net.worker_process_restarts", "gauge"],
    ["ASP.NET", None, "Request Wait Time", "exchange.asp_net.request_wait_time", "gauge"],
    ["ASP.NET Applications", None, "Requests In Application Queue", "exchange.asp_net.requests_in_queue", "gauge"],
    ["ASP.NET Applications", None, "Requests Executing", "exchange.asp_net.requests_executing", "gauge"],
    ["ASP.NET Applications", None, "Requests/Sec", "exchange.asp_net.requests_persec", "gauge"],

    # RPC Client Access Counters
    ["MSExchange RpcClientAccess", None, "RPC Averaged Latency", "exchange.rpc.averaged_latency", "gauge"],
    ["MSExchange RpcClientAccess", None, "RPC Requests", "exchange.rpc.requests", "gauge"],
    ["MSExchange RpcClientAccess", None, "RPC Active User Count", "exchange.rpc.active_user_count", "gauge"],
    ["MSExchange RpcClientAccess", None, "RPC Connection Count", "exchange.rpc.conn_count", "gauge"],
    ["MSExchange RpcClientAccess", None, "RPC Operations/sec", "exchange.rpc.ops_persec", "gauge"],
    ["MSExchange RpcClientAccess", None, "User Count", "exchange.rpc.user_count", "gauge"],

    # HTTP Proxy Counters
    ["MSExchange HttpProxy", None, "MailboxServerLocator Average Latency", "exchange.httpproxy.server_locator_latency", "gauge"],
    ["MSExchange HttpProxy", None, "Average Authentication Latency", "exchange.httpproxy.avg_auth_latency", "gauge"],
    ["MSExchange HttpProxy", None, "Average ClientAccess Server Processing Latency", "exchange.httpproxy.clientaccess_processing_latency", "gauge"],
    ["MSExchange HttpProxy", None, "Mailbox Server Proxy Failure Rate", "exchange.httpproxy.mailbox_proxy_failure_rate", "gauge"],
    ["MSExchange HttpProxy", None, "Outstanding Proxy Requests", "exchange.httpproxy.outstanding_requests", "gauge"],
    ["MSExchange HttpProxy", None, "Proxy Requests/Sec", "exchange.httpproxy.proxy_requests_persec", "gauge"],
    ["MSExchange HttpProxy", None, "Requests/Sec", "exchange.httpproxy.requests_persec", "gauge"],

    # Information Store Counters
    ["MSExchangeIS Store", None, "RPC Requests", "exchange.is.store.rpc_requests", "gauge"],
    ["MSExchangeIS Client Type", None,  "RPC Average Latency", "exchange.is.clienttype.rpc_latency", "gauge"],
    ["MSExchangeIS Store", None, "RPC Average Latency", "exchange.is.store.rpc_latency", "gauge"],
    ["MSExchangeIS Store", None, "RPC Operations/sec", "exchange.is.store.rpc_ops_persec", "gauge"],
    ["MSExchangeIS Client Type", None, "RPC Operations/sec", "exchange.is.clienttype.rpc_ops_persec", "gauge"],

    # Client Access Server Counters
    ["MSExchange ActiveSync", None, "Requests/sec", "exchange.activesync.requests_persec", "gauge"],
    ["MSExchange ActiveSync", None, "Ping Commands Pending", "exchange.activesync.ping_pending", "gauge"],
    ["MSExchange ActiveSync", None, "Sync Commands/sec", "exchange.activesync.sync_persec", "gauge"],
    ["MSExchange OWA", None, "Current Unique Users", "exchange.owa.unique_users", "gauge"],
    ["MSExchange OWA", None, "Requests/sec", "exchange.owa.requests_persec", "gauge"],
    ["MSExchangeAutodiscover", None, "Requests/sec", "exchange.autodiscover.requests_persec", "gauge"],
    ["MSExchangeWS", None, "Requests/sec", "exchange.ws.requests_persec", "gauge"],
    ["Web Service", "_Total", "Current Connections", "exchange.ws.current_connections_total", "gauge"],
    ["Web Service", "Current Connections", "exchange.ws.current_connections_default_website", "gauge"],
    ["Web Service", "_Total", "Connection Attempts/sec", "exchange.ws.connection_attempts", "gauge"],
    ["Web Service", "_Total", "Other Request Methods/sec", "exchange.ws.other_attempts", "gauge"],

    # Workload Management Counters
    ["MSExchange WorkloadManagement Workloads", None, "ActiveTasks", "exchange.workload_management.active_tasks", "gauge"],
    ["MSExchange WorkloadManagement Workloads", None, "CompletedTasks", "exchange.workload_management.completed_tasks", "gauge"],
    ["MSExchange WorkloadManagement Workloads", None, "QueuedTasks", "exchange.workload_management.queued_tasks", "gauge"],

]
class ExchangeServerCheck(AgentCheck):
    """
    WMI check.

    Windows only.
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self._countersettypes = {}
        self._counters = {}
        self._metrics = {}
        self._tags = {}

        try:
            for instance in instances:
                key = hash_mutable(instance)

                cfg_tags = instance.get('tags')
                if cfg_tags is not None:
                    tags = cfg_tags.join(",")
                    self._tags[key] = list(tags) if tags else []

                # list of the metrics.  Each entry is itself an entry,
                # which is the pdh name, datadog metric name, type, and the
                # pdh counter object
                self._metrics[key] = []
                for counterset, inst_name, counter_name, dd_name, mtype in DEFAULT_COUNTERS:
                    m = getattr(self, mtype.lower())
                    obj = WinPDHCounter(counterset, counter_name, self.log)
                    entry = [inst_name, dd_name, m, obj]
                    self.log.debug("entry: %s" % str(entry))
                    self._metrics[key].append(entry)

        except Exception as e:
            self.log.debug("Exception in PDH init: %s", str(e))
            raise

    def check(self, instance):
        key = hash_mutable(instance)
        for inst_name, dd_name, metric_func, counter in self._metrics[key]:
            vals = counter.get_all_values()
            for key, val in vals.iteritems():
                tags = []
                if key in self._tags:
                    tags = self._tags[key]

                if not counter.is_single_instance():
                    tag = "instance=%s" % key
                    tags.append(tag)
                metric_func(dd_name, val, tags)
