# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urllib.parse import urljoin

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.n8n.metrics import METRIC_MAP, RENAME_LABELS_MAP

DEFAULT_READY_ENDPOINT = '/healthz/readiness'


class N8nCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'n8n'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances=None):
        super(N8nCheck, self).__init__(
            name,
            init_config,
            instances,
        )
        self.openmetrics_endpoint = self.instance["openmetrics_endpoint"]
        self.tags = self.instance.get('tags', [])
        self._ready_endpoint = DEFAULT_READY_ENDPOINT

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': RENAME_LABELS_MAP,
        }

    def _check_n8n_readiness(self):
        endpoint = urljoin(self.openmetrics_endpoint, self._ready_endpoint)
        response = self.http.get(endpoint)

        # Determine metric value and status_code tag
        if response.status_code is None:
            self.log.warning("The readiness endpoint did not return a status code")
            metric_value = 0
            metric_tags = self.tags + ['status_code:null']
        elif response.status_code == 200:
            # Ready - submit 1
            metric_value = 1
            metric_tags = self.tags + [f'status_code:{response.status_code}']
        else:
            # Not ready - submit 0
            metric_value = 0
            metric_tags = self.tags + [f'status_code:{response.status_code}']

        # Submit metric with appropriate value and status_code tag
        self.gauge('readiness.check', metric_value, tags=metric_tags)

    def check(self, instance):
        super().check(instance)
        self._check_n8n_readiness()
