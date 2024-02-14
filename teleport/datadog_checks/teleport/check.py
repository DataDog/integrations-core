# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck  # noqa: F401

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class TeleportCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'teleport'

    def __init__(self, name, init_config, instances):
        super(TeleportCheck, self).__init__(name, init_config, instances)
        self.diagnostic_url = self.instance.get("diagnostic_url")
        # Use self.instance to read the check configuration
        # self.url = self.instance.get("url")

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
            response = self.http.get(self.diagnostic_url + "/healthz")
            response.raise_for_status()
            self.service_check("health.up", AgentCheck.OK)
        except Exception as e:
            self.service_check("health.up", AgentCheck.CRITICAL, message=str(e))

        # This is how you submit metrics
        # There are different types of metrics that you can submit (gauge, event).
        # More info at https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck
        # self.gauge("test", 1.23, tags=['foo:bar'])

        # Perform database queries using the Query Manager
        # self._query_manager.execute()

        # This is how you use the persistent cache. This cache file based and persists across agent restarts.
        # If you need an in-memory cache that is persisted across runs
        # You can define a dictionary in the __init__ method.
        # self.write_persistent_cache("key", "value")
        # value = self.read_persistent_cache("key")

        # If your check ran successfully, you can send the status.
        # More info at
        # https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.service_check
        # self.service_check("can_connect", AgentCheck.OK)

        # If it didn't then it should send a critical service check
        self.service_check("health.up", AgentCheck.CRITICAL)
