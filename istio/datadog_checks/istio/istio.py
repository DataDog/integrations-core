# (C) Datadog, Inc. 2018-Present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck

from .legacy_1_4 import LegacyIstioCheck_1_4


class Istio(OpenMetricsBaseCheck):

    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]
        if instance.get('istiod_endpoint'):
            return super(Istio, cls).__new__(cls)
        else:
            return LegacyIstioCheck_1_4(name, init_config, instances)

    def check(self, instance):
        raise NotImplementedError()
