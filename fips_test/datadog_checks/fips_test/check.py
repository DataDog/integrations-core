# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from .const import SERVICE_CHECK_HTTP

from datadog_checks.base import AgentCheck  # noqa: F401

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class FIPSTestCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'fips_test'

    def __init__(self, name, init_config, instances):
        super(FIPSTestCheck, self).__init__(name, init_config, instances)

        self.http_endpoint = self.instance.get('http_endpoint', 'https://localhost:443')
        self.rmi_endpoint = self.instance.get('rmi_endpoint', 'service:jmx:rmi:///jndi/rmi://localhost:1099/jmxrmi')
        self.socket_endpoint = self.instance.get('socket_endpoint', 'localhost:8080')
        self.ssh_endpoint = self.instance.get('ssh_endpoint', 'localhost:22')

        # If the check is going to perform SQL queries you should define a query manager here.
        # More info at
        # https://datadoghq.dev/integrations-core/base/databases/#datadog_checks.base.utils.db.core.QueryManager
        # sample_query = {
        #     "name": "sample",
        #     "query": "SELECT * FROM sample_table",
        #     "columns": [
        #         {"name": "metric", "type": "gauge"}
        #     ],
        # }
        # self._query_manager = QueryManager(self, self.execute_query, queries=[sample_query])
        # self.check_initializations.append(self._query_manager.compile_queries)

    def check(self, _):
        # type: (Any) -> None
        # The following are useful bits of code to help new users get started.

        # Perform HTTP Requests with our HTTP wrapper.
        # More info at https://datadoghq.dev/integrations-core/base/http/
        try:
            self.http.get(self.http_endpoint)
            self.service_check(SERVICE_CHECK_HTTP, AgentCheck.OK)
        except Exception as e:
            self.service_check(SERVICE_CHECK_HTTP, AgentCheck.CRITICAL, message=str(e))

        # This is how you submit metrics
        # There are different types of metrics that you can submit (gauge, event).
        # More info at https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck
        # self.gauge("test", 1.23, tags=['foo:bar'])

        # Perform database queries using the Query Manager
        # self._query_manager.execute()
