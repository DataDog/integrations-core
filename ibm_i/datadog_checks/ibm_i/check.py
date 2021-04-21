# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import closing, suppress

import pyodbc

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db import QueryManager

from . import queries
from .config_models import ConfigMixin


class IbmICheck(AgentCheck, ConfigMixin):
    def __init__(self, name, init_config, instances):
        super(IbmICheck, self).__init__(name, init_config, instances)

        self._connection = None
        self._query_manager = None

        self.check_initializations.append(self.set_up_query_manager)

    def check(self, _):
        try:
            self._query_manager.execute()
        except Exception:
            self.log.error('An error occurred, resetting IBM i connection')
            with suppress(Exception):
                self.connection.close()

            self._connection = None

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
        self._query_manager = QueryManager(
            self,
            self.execute_query,
            tags=self.config.tags,
            queries=[
                queries.DiskUsage,
            ],
        )
