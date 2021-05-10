# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing, suppress
from datetime import datetime

import pyodbc

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from . import queries
from .config_models import ConfigMixin


class IbmICheck(AgentCheck, ConfigMixin):
    SERVICE_CHECK_NAME = "ibmi.can_connect"

    def __init__(self, name, init_config, instances):
        super(IbmICheck, self).__init__(name, init_config, instances)

        self._connection = None
        self._query_manager = None

        self.check_initializations.append(self.set_up_query_manager)

    def check(self, _):
        check_start = datetime.now()
        # If we don't have a query manager yet, try to set it up
        if not self._query_manager:
            self.set_up_query_manager()

        # Do not try to send metrics if we can't tag them with a correct hostname
        if self._query_manager:
            try:
                self._query_manager.execute()
                check_status = AgentCheck.OK
            except Exception as e:
                self.warning('An error occurred, resetting IBM i connection: %s', e)
                check_status = AgentCheck.CRITICAL
                with suppress(Exception):
                    self.connection.close()

                self._connection = None

            self.service_check(
                self.SERVICE_CHECK_NAME,
                check_status,
                tags=self.config.tags,
                hostname=self._query_manager.hostname
            )
        else:
            self.warning('No hostname found, skipping check run')

        check_end = datetime.now()
        check_duration = check_end - check_start
        self.log.debug("Check duration: {}".format(check_duration))

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
            ]
            if system_info['os_version'] > 7 or (system_info['os_version'] == 7 and system_info['os_release'] >= 3):
                query_list.append(queries.SubsystemInfo)

            self._query_manager = QueryManager(
                self,
                self.execute_query,
                tags=self.config.tags,
                queries=query_list,
                hostname=system_info['hostname'],
            )
            self._query_manager.compile_queries()

    def fetch_system_info(self):
        try:
            return self.system_info_query()
        except Exception as e:
            self.warning('An error occurred while fetching system information, resetting IBM i connection: %s', e)
            with suppress(Exception):
                self.connection.close()

            self._connection = None

    def system_info_query(self):
        query = "SELECT HOST_NAME, OS_VERSION, OS_RELEASE FROM SYSIBMADM.ENV_SYS_INFO"
        results = list(self.execute_query(query)) # type: List[Tuple[str]]
        if len(results) == 0:
            self.log.error("Couldn't find hostname on the remote system.")
            return None
        if len(results) > 1:
            self.log.error("Too many results returned by system query. Expected 1, got {}".format(
                len(results)
            ))
            return None

        info_row = results[0]
        if len(info_row) != 3:
            self.log.error("Expected 3 columns in system info query, got {}".format(len(hostname_row)))
            return None

        hostname = info_row[0]
        try:
            os_version = int(info_row[1])
        except ValueError:
            self.log.error("Expected integer for OS version, got {}".format(len(info_row[1])))
            return None

        try:
            os_release = int(info_row[2])
        except ValueError:
            self.log.error("Expected integer for OS release, got {}".format(len(info_row[2])))
            return None

        return { "hostname": hostname, "os_version": os_version, "os_release": os_release }
