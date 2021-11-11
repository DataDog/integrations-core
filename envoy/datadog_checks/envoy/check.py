# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

METRIC_MAP = {

}

LABEL_MAP = {
    'cluster_name': 'envoy_cluster'
}

class EnvoyCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'envoy'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)


    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': LABEL_MAP,
        }
