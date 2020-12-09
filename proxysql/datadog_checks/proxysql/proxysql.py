# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing, contextmanager

import pymysql
import pymysql.cursors

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.db import QueryManager

from .queries import (
    STATS_COMMAND_COUNTERS,
    STATS_MEMORY_METRICS,
    STATS_MYSQL_CONNECTION_POOL,
    STATS_MYSQL_GLOBAL,
    STATS_MYSQL_QUERY_RULES,
    STATS_MYSQL_USERS,
    VERSION_METADATA,
)
from .ssl_utils import make_insecure_ssl_client_context, make_secure_ssl_client_context

ADDITIONAL_METRICS_MAPPING = {
    'command_counters_metrics': STATS_COMMAND_COUNTERS,
    'connection_pool_metrics': STATS_MYSQL_CONNECTION_POOL,
    'users_metrics': STATS_MYSQL_USERS,
    'memory_metrics': STATS_MEMORY_METRICS,
    'query_rules_metrics': STATS_MYSQL_QUERY_RULES,
}


class ProxysqlCheck(AgentCheck):

    SERVICE_CHECK_NAME = "can_connect"
    __NAMESPACE__ = "proxysql"

    def __init__(self, name, init_config, instances):
        super(ProxysqlCheck, self).__init__(name, init_config, instances)
        self.host = self.instance.get("host", "")
        self.port = int(self.instance.get("port", 0))
        self.user = self.instance.get("username", "")
        self.password = str(self.instance.get("password", ""))

        if not all((self.host, self.port, self.user, self.password)):
            raise ConfigurationError("ProxySQL host, port, username and password are needed")

        self.tls_verify = self.instance.get("tls_verify", False)
        self.validate_hostname = self.instance.get("validate_hostname", True)
        self.tls_ca_cert = self.instance.get("tls_ca_cert")
        self.connect_timeout = self.instance.get("connect_timeout", 10)
        self.read_timeout = self.instance.get("read_timeout")

        self.tags = self.instance.get("tags", [])
        self.tags.append("proxysql_server:{}".format(self.host))
        self.tags.append("proxysql_port:{}".format(self.port))

        manager_queries = [STATS_MYSQL_GLOBAL]
        if self.is_metadata_collection_enabled():
            # Add the query to collect the ProxySQL version
            manager_queries.append(VERSION_METADATA)

        additional_metrics = self.instance.get("additional_metrics", [])
        for additional_group in additional_metrics:
            if additional_group not in ADDITIONAL_METRICS_MAPPING:
                raise ConfigurationError(
                    "There is no additional metric group called '{}' for the ProxySQL integration, it should be one "
                    "of ({})".format(
                        additional_group,
                        ", ".join(ADDITIONAL_METRICS_MAPPING),
                    )
                )
            manager_queries.append(ADDITIONAL_METRICS_MAPPING[additional_group])
        self._connection = None
        self._query_manager = QueryManager(self, self.execute_query_raw, queries=manager_queries, tags=self.tags)
        self.check_initializations.append(self._query_manager.compile_queries)

    def check(self, _):
        with self.connect() as conn:
            self._connection = conn
            self._query_manager.execute()

    def execute_query_raw(self, query):
        with closing(self._connection.cursor()) as cursor:
            cursor.execute(query)
            if cursor.rowcount < 1:
                self.log.warning("Failed to fetch records from query: `%s`.", query)
                return []

            return cursor.fetchall()

    @contextmanager
    def connect(self):
        if self.tls_verify:
            # If ca_cert is None, will load the default certificates
            ssl_context = make_secure_ssl_client_context(
                ca_cert=self.tls_ca_cert, check_hostname=self.validate_hostname
            )
        else:
            ssl_context = make_insecure_ssl_client_context()

        db = None
        try:
            db = pymysql.connect(
                host=self.host,
                user=self.user,
                port=self.port,
                passwd=self.password,
                connect_timeout=self.connect_timeout,
                read_timeout=self.read_timeout,
                ssl=ssl_context,
            )
            self.log.debug("Connected to ProxySQL")
            yield db
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.tags)
            self.log.exception("Can't connect to ProxySQL")
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.tags)
        finally:
            if db:
                db.close()
