# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.quarkus.metrics import METRIC_MAP


class QuarkusCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'quarkus'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
        }
