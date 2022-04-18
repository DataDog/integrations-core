# (C) Datadog, Inc. 2022-present
# (C) 2018 Aerospike, Inc.
# (C) 2017 Red Sift
# (C) 2015 Pippio, Inc. All rights reserved.
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class AerospikeCheckV2(OpenMetricsBaseCheckV2):

    __NAMESPACE__ = 'aerospike'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        if 'metrics' in self.instance:
            # AerospikeCheck has a 'metrics' parameter which should be warned against using with openmetrics_endpoint
            self.warning(
                "Do not use 'metrics' parameter with 'openmetrics_endpoint'. "
                "Use 'extra_metrics' or 'exclude_metrics*' settings instead."
            )

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': {'cluster_name': 'aerospike_cluster', 'service': 'aerospike_service'},
        }
