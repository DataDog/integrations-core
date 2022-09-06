# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import ACME_METRICS, CERT_METRICS, CONTROLLER_METRICS, TYPE_OVERRIDES


class CertManagerCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'cert_manager'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(CertManagerCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        metric_map = dict(CONTROLLER_METRICS)
        metric_map.update(ACME_METRICS)
        metric_map.update(CERT_METRICS)

        return {'metrics': construct_metrics_config(metric_map, TYPE_OVERRIDES)}


def construct_metrics_config(metric_map, type_overrides):
    metrics = []
    for raw_metric_name, metric_name in metric_map.items():
        config = {raw_metric_name: {'name': metric_name}}
        if raw_metric_name in type_overrides:
            config[raw_metric_name]['type'] = type_overrides[raw_metric_name]

        metrics.append(config)

    return metrics
