# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.celery.metrics import METRIC_MAP


class CeleryCheck(OpenMetricsBaseCheckV2):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'celery.flower'

    DEFAULT_METRIC_LIMIT = 0  # No limit on the number of metrics collected

    def __init__(self, name, init_config, instances):
        super(CeleryCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
        }
