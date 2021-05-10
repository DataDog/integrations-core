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
        # If we don't have a hostname yet, try to fetch it
        if not self._query_manager.hostname:
            self._query_manager.hostname = self.fetch_hostname()

        # Do not try to send metrics if we can't tag them with a correct hostname
        if self._query_manager.hostname:
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

    def fetch_hostname(self):
        try:
            return self.hostname_query()
        except Exception as e:
            self.warning('An error occurred while fetching the hostname, resetting IBM i connection: %s', e)
            with suppress(Exception):
                self.connection.close()

            self._connection = None

    def hostname_query(self):
        query = "SELECT HOST_NAME FROM SYSIBMADM.ENV_SYS_INFO"
        results = list(self.execute_query(query)) # type: List[Tuple[str]]
        if len(results) == 0:
            self.log.error("Couldn't find hostname on the remote system.")
            return None
        if len(results) > 1:
            self.log.error("Too many results returned by system query. Expected 1, got {}".format(
                len(results)
            ))
            return None

        hostname_row = results[0]
        if len(hostname_row) != 1:
            self.log.error("Expected 1 column in hostname query, got {}".format(len(hostname_row)))
            return None

        return hostname_row[0]

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
        hostname = self.fetch_hostname()
        self._query_manager = QueryManager(
            self,
            self.execute_query,
            tags=self.config.tags,
            queries=[
                queries.DiskUsage,
                queries.CPUUsage,
                queries.JobStatus,
                queries.JobMemoryUsage,
                queries.MemoryInfo,
                queries.SubsystemInfo,
            ],
            hostname=hostname,
        )
        self.check_initializations.append(self._query_manager.compile_queries)
