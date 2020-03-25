from collections import defaultdict
from contextlib import closing, contextmanager

import pymysql
import pymysql.cursors

from datadog_checks.base import AgentCheck
from datadog_checks.errors import ConfigurationError

GAUGE = "gauge"
RATE = "rate"
COUNT = "count"
MONOTONIC = "monotonic_count"

STATS_MYSQL_GLOBAL = {
    "Active_Transactions": ("proxysql.active_transactions", GAUGE),
    "Query_Processor_time_nsec": ("proxysql.query_processor_time_nsec", GAUGE),
    "Questions": ("proxysql.questions", RATE),
    "Slow_queries": ("proxysql.slow_queries", RATE),
    "SQLite3_memory_bytes": ("proxysql.sqlite3_memory_bytes", GAUGE),
    "Client_Connections_aborted": ("proxysql.client.connections_aborted", RATE),
    "Client_Connections_connected": ("proxysql.client.connections_connected", GAUGE),
    "Client_Connections_created": ("proxysql.client.connections_created", RATE),
    "Client_Connections_non_idle": ("proxysql.client.connections_non_idle", GAUGE),
    "Server_Connections_aborted": ("proxysql.server.connections_aborted", RATE),
    "Server_Connections_connected": ("proxysql.server.connections_connected", GAUGE),
    "Server_Connections_created": ("proxysql.server.connections_created", RATE),
    "Backend_query_time_nsec": ("proxysql.backend.query_time_nsec", GAUGE),
    "mysql_backend_buffers_bytes": ("proxysql.mysql.backend_buffers_bytes", GAUGE),
    "mysql_frontend_buffers_bytes": ("proxysql.mysql.frontend_buffers_bytes", GAUGE),
    "mysql_session_internal_bytes": ("proxysql.mysql.session_internal_bytes", GAUGE),
    "MySQL_Thread_Workers": ("proxysql.mysql.thread_workers", GAUGE),
    "MySQL_Monitor_Workers": ("proxysql.mysql.monitor_workers", GAUGE),
    "ConnPool_get_conn_success": ("proxysql.pool.conn_success", RATE),
    "ConnPool_get_conn_failure": ("proxysql.pool.conn_failure", RATE),
    "ConnPool_get_conn_immediate": ("proxysql.pool.conn_immediate", RATE),
    "ConnPool_memory_bytes": ("proxysql.pool.memory_bytes", GAUGE),
    "Stmt_Client_Active_Total": ("proxysql.client.statements.active_total", GAUGE),
    "Stmt_Client_Active_Unique": ("proxysql.client.statements.active_unique", GAUGE),
    "Stmt_Server_Active_Total": ("proxysql.server.statements.active_total", GAUGE),
    "Stmt_Server_Active_Unique": ("proxysql.server.statements.active_unique", GAUGE),
    "Stmt_Cached": ("proxysql.statements.cached", GAUGE),
    "Query_Cache_Entries": ("proxysql.query_cache.entries", GAUGE),
    "Query_Cache_Memory_bytes": ("proxysql.query_cache.memory_bytes", GAUGE),
    "Query_Cache_Purged": ("proxysql.query_cache.purged", RATE),
    "Query_Cache_bytes_IN": ("proxysql.query_cache.bytes_in", GAUGE),
    "Query_Cache_bytes_OUT": ("proxysql.query_cache.bytes_out", GAUGE),
    "Query_Cache_count_GET": ("proxysql.query_cache.get.count", GAUGE),
    "Query_Cache_count_GET_OK": ("proxysql.query_cache.get_ok.count", GAUGE),
    "Query_Cache_count_SET": ("proxysql.query_cache.set.count", GAUGE),
}

STATS_COMMAND_COUNTERS = {
    "Total_Time_ms": ("proxysql.performance.command.total_time_ms", RATE),
    "Total_cnt": ("proxysql.performance.command.total_count", MONOTONIC),
    "cnt_100us": ("proxysql.performance.command.cnt_100us", MONOTONIC),
    "cnt_500us": ("proxysql.performance.command.cnt_500us", MONOTONIC),
    "cnt_1ms": ("proxysql.performance.command.cnt_1ms", MONOTONIC),
    "cnt_5ms": ("proxysql.performance.command.cnt_5ms", MONOTONIC),
    "cnt_10ms": ("proxysql.performance.command.cnt_10ms", MONOTONIC),
    "cnt_50ms": ("proxysql.performance.command.cnt_50ms", MONOTONIC),
    "cnt_100ms": ("proxysql.performance.command.cnt_100ms", MONOTONIC),
    "cnt_500ms": ("proxysql.performance.command.cnt_500ms", MONOTONIC),
    "cnt_1s": ("proxysql.performance.command.cnt_1s", MONOTONIC),
    "cnt_5s": ("proxysql.performance.command.cnt_5s", MONOTONIC),
    "cnt_10s": ("proxysql.performance.command.cnt_10s", MONOTONIC),
    "cnt_INFs": ("proxysql.performance.command.cnt_INFs", MONOTONIC),
}

STATS_MYSQL_CONNECTION_POOL = {
    "Connections_used": ("proxysql.pool.connections_used", GAUGE),
    "Connections_free": ("proxysql.pool.connections_free", GAUGE),
    "Connections_ok": ("proxysql.pool.connections_ok", RATE),
    "Connections_error": ("proxysql.pool.connections_error", RATE),
    "Queries": ("proxysql.pool.queries", RATE),
    "Bytes_data_sent": ("proxysql.pool.bytes_data_sent", RATE),
    "Bytes_data_recv": ("proxysql.pool.bytes_data_recv", RATE),
    "Latency_us": ("proxysql.pool.latency_ms", GAUGE),
}

STATS_MEMORY_METRICS = {
    "SQLite3_memory_bytes": ("proxysql.memory.sqlite3_memory", GAUGE),
    "jemalloc_resident": ("proxysql.memory.jemalloc_resident", GAUGE),
    "jemalloc_active": ("proxysql.memory.jemalloc_active", GAUGE),
    "jemalloc_allocated": ("proxysql.memory.jemalloc_allocated", GAUGE),
    "jemalloc_mapped": ("proxysql.memory.jemalloc_mapped", GAUGE),
    "jemalloc_metadata": ("proxysql.memory.jemalloc_metadata", GAUGE),
    "jemalloc_retained": ("proxysql.memory.jemalloc_retained", GAUGE),
    "Auth_memory": ("proxysql.memory.auth_memory", GAUGE),
    "query_digest_memory": ("proxysql.memory.query_digest_memory", GAUGE),
    "stack_memory_mysql_threads": ("proxysql.memory.stack_memory_mysql_threads", GAUGE),
    "stack_memory_admin_threads": ("proxysql.memory.stack_memory_admin_threads", GAUGE),
    "stack_memory_cluster_threads": ("proxysql.memory.stack_memory_cluster_threads", GAUGE),
}

STATS_MYSQL_USERS = {
    "User_Frontend_Connections": ("proxysql.frontend.user_connections", GAUGE),
    "User_Frontend_Max_Connections": ("proxysql.frontend.user_max_connections", GAUGE),
}

STATS_MYSQL_QUERY_RULES = {
    "Query_Rule_Hits": ("proxysql.query_rules.rule_hits", RATE),
}


class ProxysqlCheck(AgentCheck):

    SERVICE_CHECK_NAME = "proxysql.can_connect"

    def check(self, instance):
        host, port, user, password, tags, additional_metrics, connect_timeout, read_timeout = self._get_config(instance)

        if not host or not port or not user or not password:
            raise ConfigurationError("ProxySQL host, port, user and password are needed")

        with self._connect(host, port, user, password, tags, connect_timeout, read_timeout) as conn:
            self._collect_metrics(conn, tags, additional_metrics)

    def _collect_metrics(self, conn, tags, additional_metrics):
        """Collects all the different types of ProxySQL metrics and submits them to Datadog"""
        global_stats = self._get_global_stats(conn)
        self._send_simple_tag_metrics(global_stats, STATS_MYSQL_GLOBAL, tags)

        if 'command_counters_metrics' in additional_metrics:
            command_counters_stats = self._get_command_counters(conn)
            self._send_extra_tag_metrics(command_counters_stats, STATS_COMMAND_COUNTERS, tags)

        if 'connection_pool_metrics' in additional_metrics:
            conn_pool_stats = self._get_connection_pool_stats(conn)
            self._send_extra_tag_metrics(conn_pool_stats, STATS_MYSQL_CONNECTION_POOL, tags)

        if 'memory_metrics' in additional_metrics:
            memory_stats = self._get_memory_stats(conn)
            self._send_simple_tag_metrics(memory_stats, STATS_MEMORY_METRICS, tags)

        if 'users_metrics' in additional_metrics:
            user_stats = self._get_user_stats(conn)
            self._send_extra_tag_metrics(user_stats, STATS_MYSQL_USERS, tags)

        if 'query_rules_metrics' in additional_metrics:
            query_rules_stats = self._get_query_rules_stats(conn)
            self._send_extra_tag_metrics(query_rules_stats, STATS_MYSQL_QUERY_RULES, tags)

    def _send_simple_tag_metrics(self, stats, metrics_definition, tags):
        for proxysql_metric_name, metric_details in metrics_definition.items():
            metric_name, metric_type = metric_details
            metric_tags = list(tags)
            self._send_metric(metric_name, metric_type, float(stats.get(proxysql_metric_name)), metric_tags)

    def _send_extra_tag_metrics(self, stats, metrics_definition, tags):
        for proxysql_metric_name, metric_details in metrics_definition.items():
            metric_name, metric_type = metric_details

            for metric in stats.get(proxysql_metric_name, []):
                metric_tags = list(tags)
                tag, value = metric
                metric_tags.append(tag)
                self._send_metric(metric_name, metric_type, float(value), metric_tags)

    def _send_metric(self, metric_name, metric_type, metric_value, metric_tags):
        if metric_type == RATE:
            self.rate(metric_name, metric_value, tags=metric_tags)
        elif metric_type == GAUGE:
            self.gauge(metric_name, metric_value, tags=metric_tags)
        elif metric_type == COUNT:
            self.count(metric_name, metric_value, tags=metric_tags)
        elif metric_type == MONOTONIC:
            self.monotonic_count(metric_name, metric_value, tags=metric_tags)

    def _fetch_stats(self, conn, query, stats_name):
        try:
            with closing(conn.cursor()) as cursor:
                cursor.execute(query)

                if cursor.rowcount < 1:
                    self.warning("Failed to fetch records from %s.", stats_name)
                    return []

                return cursor.fetchall()
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as e:
            self.warning("ProxySQL %s unavailable at this time: %s", stats_name, str(e))
            return []

    def _get_global_stats(self, conn):
        """Fetch the global ProxySQL stats."""
        query = "SELECT * FROM stats.stats_mysql_global"
        return {row["Variable_Name"]: row["Variable_Value"] for row in self._fetch_stats(conn, query, 'global_stats')}

    def _get_command_counters(self, conn):
        """Fetch ProxySQL command counters stats"""
        query = "SELECT * FROM stats.stats_mysql_commands_counters"
        metrics = defaultdict(list)

        for row in self._fetch_stats(conn, query, 'command_counters_stats'):
            command_tag = "proxysql_command:%s" % row["Command"]
            metrics["Total_Time_ms"].append((command_tag, str(float(row["Total_Time_us"]) / 1000)))
            metrics["Total_cnt"].append((command_tag, row["Total_cnt"]))
            metrics["cnt_100us"].append((command_tag, row["cnt_100us"]))
            metrics["cnt_500us"].append((command_tag, row["cnt_500us"]))
            metrics["cnt_1ms"].append((command_tag, row["cnt_1ms"]))
            metrics["cnt_5ms"].append((command_tag, row["cnt_5ms"]))
            metrics["cnt_10ms"].append((command_tag, row["cnt_10ms"]))
            metrics["cnt_50ms"].append((command_tag, row["cnt_50ms"]))
            metrics["cnt_100ms"].append((command_tag, row["cnt_100ms"]))
            metrics["cnt_500ms"].append((command_tag, row["cnt_500ms"]))
            metrics["cnt_1s"].append((command_tag, row["cnt_1s"]))
            metrics["cnt_5s"].append((command_tag, row["cnt_5s"]))
            metrics["cnt_10s"].append((command_tag, row["cnt_10s"]))
            metrics["cnt_INFs"].append((command_tag, row["cnt_INFs"]))

        return metrics

    def _get_connection_pool_stats(self, conn):
        """Fetch ProxySQL connection pool stats"""
        query = "SELECT * FROM stats.stats_mysql_connection_pool"

        stats = defaultdict(list)
        for row in self._fetch_stats(conn, query, 'connection_pool_stats'):
            node_tag = "proxysql_db_node:%s" % row["srv_host"]
            stats["Connections_used"].append((node_tag, row["ConnUsed"]))
            stats["Connections_free"].append((node_tag, row["ConnFree"]))
            stats["Connections_ok"].append((node_tag, row["ConnOK"]))
            stats["Connections_error"].append((node_tag, row["ConnERR"]))
            stats["Queries"].append((node_tag, row["Queries"]))
            stats["Bytes_data_sent"].append((node_tag, row["Bytes_data_sent"]))
            stats["Bytes_data_recv"].append((node_tag, row["Bytes_data_recv"]))
            stats["Latency_us"].append((node_tag, str(float(row["Latency_us"]) / 1000)))

        return stats

    def _get_memory_stats(self, conn):
        """Fetch ProxySQL memory stats"""
        query = "SELECT * FROM stats.stats_memory_metrics"
        return {row["Variable_Name"]: row["Variable_Value"] for row in self._fetch_stats(conn, query, 'memory_stats')}

    def _get_user_stats(self, conn):
        """Fetch ProxySQL Users Frontend connections stats"""
        query = "SELECT * FROM stats.stats_mysql_users"
        stats = defaultdict(list)

        for row in self._fetch_stats(conn, query, 'users_stats'):
            user_tag = "proxysql_mysql_user:%s" % row["username"]
            stats["User_Frontend_Connections"].append((user_tag, row["frontend_connections"]))
            stats["User_Frontend_Max_Connections"].append((user_tag, row["frontend_max_connections"]))

        return stats

    def _get_query_rules_stats(self, conn):
        """Fetch ProxySQL Users Frontend connections stats"""
        query = "SELECT * FROM stats.stats_mysql_query_rules"
        stats = defaultdict(list)

        for row in self._fetch_stats(conn, query, 'query_rules_stats'):
            stats["Query_Rule_Hits"].append(("proxysql_query_rule_id:%s" % row["rule_id"], row["hits"]))

        return stats

    def _get_config(self, instance):
        host = instance.get("server", "")
        port = int(instance.get("port", 0))

        user = instance.get("user", "")
        password = str(instance.get("pass", ""))
        tags = instance.get("tags", [])
        additional_metrics = instance.get("additional_metrics", [])
        connect_timeout = instance.get("connect_timeout", 10)
        read_timeout = instance.get("read_timeout", None)
        return host, port, user, password, tags, additional_metrics, connect_timeout, read_timeout

    @contextmanager
    def _connect(self, host, port, user, password, tags, connect_timeout, read_timeout):
        self.service_check_tags = ["server:{}".format(host), "port:{}".format(str(port))].extend(tags)

        db = None
        try:
            db = pymysql.connect(
                host=host,
                user=user,
                port=port,
                passwd=password,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                cursorclass=pymysql.cursors.DictCursor,
            )
            self.log.debug("Connected to ProxySQL")
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.service_check_tags)
            yield db
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.service_check_tags)
            self.log.exception(e)
            raise
        finally:
            if db:
                db.close()
