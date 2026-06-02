# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2


class KueueCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'kueue'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {'metrics': ['.*']}
