# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .constants import MESH_NAMESPACE, ISTIOD_NAMESPACE
from .metrics import construct_metrics_config, ISTIOD_METRICS, MESH_METRICS, TYPE_OVERRIDES


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
            self.scraper_configs.append(self._generate_config(mesh_endpoint, MESH_METRICS, MESH_NAMESPACE))
        if istiod_endpoint:
            self.scraper_configs.append(self._generate_config(istiod_endpoint, ISTIOD_METRICS, ISTIOD_METRICS))

    def _generate_config(self, endpoint, metrics, namespace):
        config = {'openmetrics_endpoint': endpoint, 'metrics': construct_metrics_config(metrics, TYPE_OVERRIDES), 'namespace': namespace}
        config.update(self.instance)
        return config

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

    def get_config_with_defaults(self, config):
        return ChainMap(config, {'metrics': config.pop('metrics')})
