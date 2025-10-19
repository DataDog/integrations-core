# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urlparse, urlunparse

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.bentoml.metrics import ENDPOINT_METRICS, METRICS


class BentomlCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'bentoml'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(BentomlCheck, self).__init__(name, init_config, instances)
        self.openmetrics_endpoint = self.instance.get('openmetrics_endpoint')
        self.base_url = self._extract_base_url(self.openmetrics_endpoint) if self.openmetrics_endpoint else None
        self.tags = self.instance.get('tags', [])

    def _extract_base_url(self, endpoint):
        parsed = urlparse(endpoint)
        path = parsed.path.rstrip('/')
        base_path = path.rsplit('/', 1)[0] if '/' in path else ''
        return urlunparse(parsed._replace(path=base_path or '/'))

    def get_default_config(self):
        return {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': [METRICS],
        }

    def check(self, instance):
        super(BentomlCheck, self).check(instance)
        if self.base_url:
            self.check_health_endpoint()

    def check_health_endpoint(self):
        for endpoint_path, metric_name in ENDPOINT_METRICS.items():
            try:
                url = f"{self.base_url}{endpoint_path}"
                response = self.http.get(url)
                response.raise_for_status()

                tags = [*self.tags, f"status_code:{response.status_code}"]
                self.gauge(metric_name, 1, tags=tags)
                self.log.debug("Successfully checked %s at %s", metric_name, url)
            except Exception as e:
                status_code = None
                if hasattr(e, 'response') and e.response is not None:
                    status_code = getattr(e.response, 'status_code', None)

                tags = [*self.tags]
                if status_code is not None:
                    tags.append(f"status_code:{status_code}")

                self.log.debug("Failed to check %s at %s: %s", metric_name, url, str(e))
                self.gauge(metric_name, 0, tags=tags)
