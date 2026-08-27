# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class DynamoCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'dynamo'

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'histogram_buckets_as_distributions': True,
            'collect_counters_with_distributions': True,
        }
