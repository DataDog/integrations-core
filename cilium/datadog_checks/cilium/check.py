# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2

from .metrics import PROMETHEUS_METRICS_MAP


class CiliumCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'cilium'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)