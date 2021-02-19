{license_header}
from typing import Any

from datadog_checks.base import AgentCheck


class {check_class}(AgentCheck):
    def check(self, _):
        # type: (Any) -> None
        # The following are useful bits of code to help new users started.

        # Perform HTTP Requests with our HTTP wrapper.
        # More info at https://datadoghq.dev/integrations-core/base/http/
        # self.http.get("<url>")

        # This is how you submit metrics
        # self.gauge("test", 1.23, tags=['foo:bar'])

        # There are different types of metrics that you can submit (events, count).
        # More info at https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck
        # self.count("count", 1.0)

        # This is how you can perform database queries.
        # You would need to define your query manager in your __init__ method.
        # More info at
        # https://datadoghq.dev/integrations-core/base/databases/#datadog_checks.base.utils.db.core.QueryManager
        # self._query_manager.execute()

        # If your check ran succesfully, you can send the status.
        # More info at
        # https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.service_check
        # self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)

        pass
