{license_header}
from typing import Any

from datadog_checks.base import AgentCheck


class {check_class}(AgentCheck):
    def __init__(self, name, init_config, instances):
        # super({check_name}, self).__init__(name, init_config, instances)

        # Define a query manager.
        # More info at
        # https://datadoghq.dev/integrations-core/base/databases/#datadog_checks.base.utils.db.core.QueryManager
        # self._query_manager = QueryManager(self, self.execute_query, queries=[queries.SomeQuery1])
        # self.check_initializations.append(self._query_manager.compile_queries)
        pass

    def check(self, _):
        # type: (Any) -> None
        # The following are useful bits of code to help new users started.

        # Perform HTTP Requests with our HTTP wrapper.
        # More info at https://datadoghq.dev/integrations-core/base/http/
        # self.http.get("<url>")

        # This is how you submit metrics
        # There are different types of metrics that you can submit (gauge, event).
        # More info at https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck
        # self.gauge("test", 1.23, tags=['foo:bar'])

        # Perform database queries using the Query Manager
        # self._query_manager.execute()

        # If your check ran successfully, you can send the status.
        # More info at
        # https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.service_check
        # self.service_check({check_name}.can_connect, AgentCheck.OK)

        pass
