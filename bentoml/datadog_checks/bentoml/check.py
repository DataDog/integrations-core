# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401

from datadog_checks.base import OpenMetricsBaseCheckV2  # noqa: F401
from datadog_checks.bentoml.metrics import METRICS, ENDPOINT_METRICS
from urllib.parse import urlparse, urlunparse

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class BentomlCheck(OpenMetricsBaseCheckV2):

    # This will be the prefix of every metric the integration sends
    __NAMESPACE__ = 'bentoml'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(BentomlCheck, self).__init__(name, init_config, instances)
        self.openmetrics_endpoint = self.instance.get('openmetrics_endpoint')
        if self.openmetrics_endpoint:
            parsed = urlparse(self.openmetrics_endpoint)
            path = parsed.path.rstrip('/')
            if '/' in path:
                base_path = path.rsplit('/', 1)[0]
            else:
                base_path = ''
            self.base_url = urlunparse(parsed._replace(path=base_path or '/'))
        else:
            self.base_url = None
        self.tags = self.instance.get('tags', [])

    def get_default_config(self):
        return {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': [METRICS],
        }

    def check(self, instance):
        super(BentomlCheck, self).check(instance)
        self.check_health_endpoint()


    def check_health_endpoint(self):
        endpoint = self.base_url
        for endpoint, metric in ENDPOINT_METRICS.items():
            url = f"{endpoint}"
            response = self.http.get(url)
            response.raise_for_status()
            if response.status_code == 200:
                self.gauge(metric, 1, tags=self.tags)
            else:
                self.log.debug(f"Failed to get {metric} from {url}")
                self.gauge(metric, 0, tags=self.tags)
