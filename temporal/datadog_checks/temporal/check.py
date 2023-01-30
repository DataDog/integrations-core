# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.temporal.config_models import ConfigMixin
from datadog_checks.temporal.metrics import METRIC_MAP


class TemporalCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'temporal.server'

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
        }
