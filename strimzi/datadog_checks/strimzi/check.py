# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.strimzi.config_models import ConfigMixin
from datadog_checks.strimzi.metrics import METRICS_MAP

from datadog_checks.base import OpenMetricsBaseCheckV2


class StrimziCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'strimzi'

    def get_default_config(self):
        return {
            "metrics": [METRICS_MAP],
        }
