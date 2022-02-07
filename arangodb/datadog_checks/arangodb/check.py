# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .config_models import ConfigMixin
from .metrics import METRIC_MAP, construct_metrics_config


class ArangodbCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'arangodb'

    def __init__(self, name, init_config, instances):
        super(ArangodbCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'openmetrics_endpoint': 'http://localhost:8529/_admin/metrics',
            'metrics': construct_metrics_config(METRIC_MAP, {}),
        }

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

    # def check(self, _):
    #
    #     self.service_check("can_connect", AgentCheck.CRITICAL)
