# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.errors import CheckException  # noqa: F401

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class TeleportCheck(OpenMetricsBaseCheckV2):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'teleport'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.diagnostic_url = self.instance.get("diagnostic_url")
        self.check_initializations.appendleft(self._parse_config)

    def check(self, _):
        try:
            super().check(_)
            response = self.http.get(self.diagnostic_url + "/healthz")
            response.raise_for_status()
            self.service_check("health.up", self.OK)
        except Exception as e:
            self.service_check("health.up", self.CRITICAL, message=str(e))
        finally:
            pass

    def _parse_config(self):
        if self.diagnostic_url:
            self.instance.setdefault("openmetrics_endpoint", self.diagnostic_url+"/metrics")

        # if diagnostic_url:
        #     # We create another config to scrape Gitaly metrics, so we have two different scrapers:
        #     # one for the main GitLab and another one for the Gitaly endpoint.
        #     config = copy.deepcopy(self.instance)
        #     config['openmetrics_endpoint'] = diagnostic_url + "/metrics"
        #     config['namespace'] = 'teleport'
        #     self.scraper_configs.append(config)
