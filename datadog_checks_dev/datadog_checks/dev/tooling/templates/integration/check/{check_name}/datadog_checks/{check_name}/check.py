{license_header}

from datadog_checks.base import AgentCheck
from datadog_checks.base.types import InitConfigType, InstanceType

from .config_models import ConfigMixin

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class {check_class}(AgentCheck, ConfigMixin):
    # This will be the prefix of every metric the integration sends
    __NAMESPACE__ = '{check_name}'

    def __init__(self, name: str, init_config: InitConfigType, instances: list[InstanceType]) -> None:
        super().__init__(name, init_config, instances)

        # Read validated, typed configuration from self.config (and self.shared_config).
        # Fields must be declared in spec.yaml and the models regenerated with `ddev validate models`.
        # self.url = self.config.url

        # If the check is going to perform SQL queries you should define a query manager here.
        # More info at
        # https://datadoghq.dev/integrations-core/base/databases/#datadog_checks.base.utils.db.core.QueryManager
        # sample_query = {{
        #     "name": "sample",
        #     "query": "SELECT * FROM sample_table",
        #     "columns": [
        #         {{"name": "metric", "type": "gauge"}}
        #     ],
        # }}
        # self._query_manager = QueryManager(self, self.execute_query, queries=[sample_query])
        # self.check_initializations.append(self._query_manager.compile_queries)

    def check(self, _: InstanceType) -> None:
        # The following are useful bits of code to help new users get started.

        # Perform HTTP Requests with our HTTP wrapper.
        # More info at https://datadoghq.dev/integrations-core/base/http/
        # try:
        #     response = self.http.get(self.url)
        #     response.raise_for_status()
        #     response_json = response.json()

        # except (HTTPError, InvalidURL, ConnectionError, Timeout):
        #     self.log.debug("Could not connect", exc_info=True)

        # except JSONDecodeError:
        #    self.log.debug("Could not parse JSON", exc_info=True)

        # except ValueError:
        #    self.log.debug("Unexpected value", exc_info=True)

        # This is how you submit metrics
        # There are different types of metrics that you can submit (gauge, event).
        # More info at https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck
        # self.gauge("test", 1.23, tags=['foo:bar'])

        # Perform database queries using the Query Manager
        # self._query_manager.execute()

        # This is how you use the persistent cache. This cache is file based and persists across agent restarts.
        # If you need an in-memory cache that is persisted across runs
        # You can define a dictionary in the __init__ method.
        # self.write_persistent_cache("key", "value")
        # value = self.read_persistent_cache("key")
        pass
