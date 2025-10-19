# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

METRICS_MAP = [
    {
        'datadog_csi_driver_node_publish_volume_attempts': {'name': 'node_publish_volume_attempts'},
        'datadog_csi_driver_node_unpublish_volume_attempts': {'name': 'node_unpublish_volume_attempts'},
    }
]


class DatadogCSIDriverCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'datadog.csi_driver'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'metrics': METRICS_MAP,
            'openmetrics_endpoint': 'http://localhost:5000/metrics',
        }

    def check(self, instance):
        super().check(instance)
