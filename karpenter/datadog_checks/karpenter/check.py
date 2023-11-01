# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class KarpenterCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'karpenter'

    def __init__(self, name, init_config, instances=None):

        super(KarpenterCheck, self).__init__(
            name,
            init_config,
            instances,
        )

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            "rename_labels": {
                "version": "go_version",
                'host': 'karpenter_host',
                'instance_type': 'karpenter_instance_type',
                'capacity_type': 'karpenter_capacity_type',
                "zone": "karpenter_zone",
                "region": "karpenter_region",
            },
        }
