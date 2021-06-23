# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .metrics import construct_metrics_config, ISTIOD_METRICS, MESH_METRICS


class IstioCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'istio'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(IstioCheckV2, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        self.scraper_configs = []
        mesh_endpoint = self.instance.get("istio_mesh_endpoint")
        istiod_endpoint = self.instance.get("istiod_endpoint")
        if not mesh_endpoint and not istiod_endpoint:
            raise ConfigurationError("Must specify at least one of the following endpoints: `istio_mesh_endpoint` or `istiod_endpoint`.")

        if mesh_endpoint:
            config = {'openmetrics_endpoint': mesh_endpoint, 'metrics': construct_metrics_config(MESH_METRICS)}
            config.update(self.instance)
            self.scraper_configs.append(config)
        if istiod_endpoint:
            config = {'openmetrics_endpoint': istiod_endpoint, 'metrics': construct_metrics_config(ISTIOD_METRICS)}
            config.update(self.instance)
            self.scraper_configs.append(config)

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

    def get_config_with_defaults(self, config):
        return ChainMap(config, {'metrics': config.pop('metrics')})
