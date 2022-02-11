# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP, construct_metrics_config


class HaproxyCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'haproxy'

    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {'metrics': construct_metrics_config(METRIC_MAP)}
