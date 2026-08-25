# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2  # noqa: F401
from datadog_checks.velero.metrics import METRIC_MAP


class VeleroCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'velero'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(VeleroCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
        }
