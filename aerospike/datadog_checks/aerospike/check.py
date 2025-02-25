# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class AerospikeCheckV2(OpenMetricsBaseCheckV2):

    __NAMESPACE__ = 'aerospike'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            # enabling histogram to be treated as distribution
            'collect_histogram_buckets': 'true',
            'histogram_buckets_as_distributions': 'true',
            'collect_counters_with_distributions': 'true',
            'rename_labels': {'cluster_name': 'aerospike_cluster', 'service': 'aerospike_service'},
        }
