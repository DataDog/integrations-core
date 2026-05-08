# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urllib.parse import urljoin, urlparse

from requests.exceptions import RequestException

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.n8n.metrics import METRIC_MAP, RENAME_LABELS_MAP

from .config_models import ConfigMixin

DEFAULT_READY_PATH = '/healthz/readiness'


class N8nCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'n8n'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self) -> dict:
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': RENAME_LABELS_MAP,
            'raw_metric_prefix': 'n8n_',
        }

    def _readiness_endpoint(self) -> str:
        parsed = urlparse(self.config.openmetrics_endpoint)
        base = f'{parsed.scheme}://{parsed.netloc}'
        return urljoin(base, DEFAULT_READY_PATH)

    def _check_n8n_readiness(self) -> None:
        endpoint = self._readiness_endpoint()
        tags = list(self.config.tags or ())

        try:
            response = self.http.get(endpoint)
        except RequestException as e:
            self.log.warning("Could not reach n8n readiness endpoint %s: %s", endpoint, e)
            self.gauge('readiness.check', 0, tags=tags + ['status_code:none'])
            return

        is_ready = response.status_code == 200
        self.gauge(
            'readiness.check',
            1 if is_ready else 0,
            tags=tags + [f'status_code:{response.status_code}'],
        )

    def check(self, instance: dict) -> None:
        self._check_n8n_readiness()
        super().check(instance)
