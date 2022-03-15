# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import METRIC_MAP, construct_metrics_config


class ArangodbCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'arangodb'

    def __init__(self, name, init_config, instances):
        super(ArangodbCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'openmetrics_endpoint': 'http://localhost:8529/_admin/metrics/v2',
            'metrics': construct_metrics_config(METRIC_MAP, {}),
        }
