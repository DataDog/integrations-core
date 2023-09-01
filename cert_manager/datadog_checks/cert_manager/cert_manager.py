# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import ACME_METRICS, CERT_METRICS, CONTROLLER_METRICS


class CertManagerCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'cert_manager'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(CertManagerCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        metric_map = dict(CONTROLLER_METRICS)
        metric_map.update(ACME_METRICS)
        metric_map.update(CERT_METRICS)

        return {'metrics': [metric_map]}
