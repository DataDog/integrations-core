# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import METRIC_MAP


class PulsarCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'pulsar'

    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            'openmetrics_endpoint': 'http://localhost:8080/metrics',
            'metrics': [METRIC_MAP],
            'rename_labels': {'cluster': 'pulsar_cluster'},
        }
