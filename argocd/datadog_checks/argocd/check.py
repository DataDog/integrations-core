# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# from typing import Any

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import API_SERVER_METRICS, APPLICATION_CONTROLLER_METRICS, REPO_SERVER_METRICS

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class ArgocdCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'argocd'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(ArgocdCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        self.scraper_configs = []
        app_controller_endpoint = self.instance.get("app_controller_endpoint")
        api_server_endpoint = self.instance.get("api_server_endpoint")
        repo_server_endpoint = self.instance.get("repo_server_endpoint")
        if not app_controller_endpoint and not repo_server_endpoint and not api_server_endpoint:
            raise ConfigurationError(
                "Must specify at least one of the following: `app_controller_endpoint`, `repo_server_endpoint` or `api_server_endpoint`."
            )

        if app_controller_endpoint:
            self.scraper_configs.append(self._generate_config(app_controller_endpoint, APPLICATION_CONTROLLER_METRICS))
        if api_server_endpoint:
            self.scraper_configs.append(self._generate_config(api_server_endpoint, API_SERVER_METRICS))
        if repo_server_endpoint:
            self.scraper_configs.append(self._generate_config(repo_server_endpoint, REPO_SERVER_METRICS))

    def _generate_config(self, endpoint, metrics):
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': metrics,
        }
        config.update(self.instance)
        return config

    def check(self, _):
        # try:
        #     response = self.http.get(self.config.health_endpoint)
        # except Exception as e:
        #     self.submit_controller_health(self.CRITICAL, message=str(e))
        # else:
        #     try:
        #         response.raise_for_status()
        #     except Exception as e:
        #         if response.status_code == 503:
        #             self.submit_controller_health(self.WARNING, message=str(e))
        #         else:
        #             self.submit_controller_health(self.CRITICAL, message=str(e))
        #     else:
        #         self.submit_controller_health(self.OK)

        super().check(_)


# class ArgocdCheck(AgentCheck):

#     # This will be the prefix of every metric and service check the integration sends
#     __NAMESPACE__ = 'argocd'

#     def __init__(self, name, init_config, instances):
#         super(ArgocdCheck, self).__init__(name, init_config, instances)

#         # Use self.instance to read the check configuration
#         # self.url = self.instance.get("url")

#         # If the check is going to perform SQL queries you should define a query manager here.
#         # More info at
#         # https://datadoghq.dev/integrations-core/base/databases/#datadog_checks.base.utils.db.core.QueryManager
#         # sample_query = {
#         #     "name": "sample",
#         #     "query": "SELECT * FROM sample_table",
#         #     "columns": [
#         #         {"name": "metric", "type": "gauge"}
#         #     ],
#         # }
#         # self._query_manager = QueryManager(self, self.execute_query, queries=[sample_query])
#         # self.check_initializations.append(self._query_manager.compile_queries)

#     def check(self, _):
#         # type: (Any) -> None
#         # The following are useful bits of code to help new users get started.

#         # Perform HTTP Requests with our HTTP wrapper.
#         # More info at https://datadoghq.dev/integrations-core/base/http/
#         # try:
#         #     response = self.http.get(self.url)
#         #     response.raise_for_status()
#         #     response_json = response.json()

#         # except Timeout as e:
#         #     self.service_check(
#         #         "can_connect",
#         #         AgentCheck.CRITICAL,
#         #         message="Request timeout: {}, {}".format(self.url, e),
#         #     )
#         #     raise

#         # except (HTTPError, InvalidURL, ConnectionError) as e:
#         #     self.service_check(
#         #         "can_connect",
#         #         AgentCheck.CRITICAL,
#         #         message="Request failed: {}, {}".format(self.url, e),
#         #     )
#         #     raise

#         # except JSONDecodeError as e:
#         #     self.service_check(
#         #         "can_connect",
#         #         AgentCheck.CRITICAL,
#         #         message="JSON Parse failed: {}, {}".format(self.url, e),
#         #     )
#         #     raise

#         # except ValueError as e:
#         #     self.service_check(
#         #         "can_connect", AgentCheck.CRITICAL, message=str(e)
#         #     )
#         #     raise

#         # This is how you submit metrics
#         # There are different types of metrics that you can submit (gauge, event).
#         # More info at https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck
#         # self.gauge("test", 1.23, tags=['foo:bar'])

#         # Perform database queries using the Query Manager
#         # self._query_manager.execute()

#         # This is how you use the persistent cache. This cache file based and persists across agent restarts.
#         # If you need an in-memory cache that is persisted across runs
#         # You can define a dictionary in the __init__ method.
#         # self.write_persistent_cache("key", "value")
#         # value = self.read_persistent_cache("key")

#         # If your check ran successfully, you can send the status.
#         # More info at
#         # https://datadoghq.dev/integrations-core/base/api/#datadog_checks.base.checks.base.AgentCheck.service_check
#         # self.service_check("can_connect", AgentCheck.OK)

#         # If it didn't then it should send a critical service check
#         self.service_check("can_connect", AgentCheck.CRITICAL)
