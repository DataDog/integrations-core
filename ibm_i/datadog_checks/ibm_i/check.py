# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing, suppress
from datetime import datetime
from typing import List, NamedTuple, Tuple

import pyodbc

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from . import queries
from .config_models import ConfigMixin

SystemInfo = NamedTuple('SystemInfo', [('hostname', str), ('os_version', int), ('os_release', int)])


class IbmICheck(AgentCheck, ConfigMixin):
    SERVICE_CHECK_NAME = "ibm_i.can_connect"

    def __init__(self, name, init_config, instances):
        super(IbmICheck, self).__init__(name, init_config, instances)

        self._connection = None
        self._query_manager = None
        self._current_errors = 0
        self.check_initializations.append(self.set_up_query_manager)

    def handle_query_error(self, error):
        self._current_errors += 1
        return error

    def _delete_connection(self, e):
        if self._connection:
            self.warning('An error occurred, resetting IBM i connection: %s', e)
            with suppress(Exception):
                self.connection.close()
            self._connection = None

    def check(self, _):
        check_start = datetime.now()
        self._current_errors = 0

        try:
            self.query_manager.execute()
            check_status = AgentCheck.OK
        except AttributeError:
            self.warning('Could not set up query manager, skipping check run')
            check_status = None
        except Exception as e:
            self._delete_connection(e)
            check_status = AgentCheck.CRITICAL

        if self._current_errors:
            self._delete_connection("query error")
            check_status = AgentCheck.CRITICAL

        if check_status is not None:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                check_status,
                tags=self.config.tags,
                hostname=self._query_manager.hostname,
            )

        check_end = datetime.now()
        check_duration = check_end - check_start
        self.log.debug("Check duration: %s", check_duration)

        if check_status is not None:
            # The list() conversion is needed as self.config.tags is a tuple
            check_duration_tags = list(self.config.tags) + ["check_id:{}".format(self.check_id)]
            self.gauge(
                "ibm_i.check.duration",
                check_duration.total_seconds(),
                check_duration_tags,
                hostname=self._query_manager.hostname,
            )

    def execute_query(self, query):
        # https://github.com/mkleehammer/pyodbc/wiki/Connection#execute
        with closing(self.connection.execute(query)) as cursor:

            # https://github.com/mkleehammer/pyodbc/wiki/Cursor
            for row in cursor:
                yield row

    @property
    def connection(self):
        if self._connection is None:
            # https://www.connectionstrings.com/as-400/
            # https://www.ibm.com/support/pages/odbc-driver-ibm-i-access-client-solutions
            connection_string = self.config.connection_string
            if not connection_string:
                connection_string = f'Driver={{{self.config.driver.strip("{}")}}};'

                if self.config.system:
                    connection_string += f'System={self.config.system};'

                if self.config.username:
                    connection_string += f'Uid={self.config.username};'

                if self.config.password:
                    connection_string += f'Pwd={self.config.password};'
                    self.register_secret(self.config.password)

            self._connection = pyodbc.connect(connection_string)

        return self._connection

    @property
    def query_manager(self):
        if self._query_manager is None:
            self.set_up_query_manager()
        return self._query_manager

    def set_up_query_manager(self):
        system_info = self.fetch_system_info()
        if system_info:
            query_list = [
                queries.DiskUsage,
                queries.CPUUsage,
                queries.JobStatus,
                queries.JobMemoryUsage,
                queries.MemoryInfo,
                queries.JobQueueInfo,
                queries.MessageQueueInfo,
            ]
            if system_info.os_version > 7 or (system_info.os_version == 7 and system_info.os_release >= 3):
                query_list.append(queries.SubsystemInfo)

            if self.config.fetch_ibm_mq_metrics and self.ibm_mq_check():
                query_list.append(queries.IBMMQInfo)

            self._query_manager = QueryManager(
                self,
                self.execute_query,
                tags=self.config.tags,
                queries=query_list,
                hostname=system_info.hostname,
                error_handler=self.handle_query_error,
            )
            self._query_manager.compile_queries()

    def ibm_mq_check(self):
        # Try to get data from the IBM MQ tables. If they're not present,
        # an exception is raised, and we return that IBM MQ is not available.
        query = "SELECT QNAME, COUNT(*) FROM TABLE(MQREADALL()) GROUP BY QNAME"
        try:
            # self.execute_query(query) yields a generator, therefore the SQL query is actually run
            # only when needed (eg. when looping through it, transforming it
            # into a list, using next on it to get the next element).
            # We do need the query to be executed, which is why we do an operation on it.
            # We use the list operation because we know it will work as long as the query doesn't
            # raise an error (if we were to use next, we'd have to take care of the case where
            # the generator rasies a StopIteration exception because the query is valid but returns 0 rows).
            list(self.execute_query(query))  # type: List[Tuple[str]]
        except Exception as e:
            self.log.debug("Couldn't find IBM MQ data, turning off IBM MQ queries: %s", e)
            return False

        return True

    def fetch_system_info(self):
        try:
            return self.system_info_query()
        except Exception as e:
            self._delete_connection(e)

    def system_info_query(self):
        query = "SELECT HOST_NAME, OS_VERSION, OS_RELEASE FROM SYSIBMADM.ENV_SYS_INFO"
        results = list(self.execute_query(query))  # type: List[Tuple[str]]
        if len(results) == 0:
            self.log.error("Couldn't find system info on the remote system.")
            return None
        if len(results) > 1:
            self.log.error("Too many results returned by system query. Expected 1, got %d", len(results))
            return None

        info_row = results[0]
        if len(info_row) != 3:
            self.log.error("Expected 3 columns in system info query, got %d", len(info_row))
            return None

        hostname = info_row[0]
        try:
            os_version = int(info_row[1])
        except ValueError:
            self.log.error("Expected integer for OS version, got %s", info_row[1])
            return None

        try:
            os_release = int(info_row[2])
        except ValueError:
            self.log.error("Expected integer for OS release, got %s", info_row[2])
            return None

        return SystemInfo(hostname=hostname, os_version=os_version, os_release=os_release)
