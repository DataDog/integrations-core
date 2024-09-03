# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class AppgateSdpCheck(OpenMetricsBaseCheckV2):

    __NAMESPACE__ = 'appgate'

    def __init__(self, name, init_config, instances):
        super(AppgateSdpCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
        }
