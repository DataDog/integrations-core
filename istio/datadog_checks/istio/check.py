# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .constants import ISTIOD_NAMESPACE
from .metrics import ISTIOD_METRICS, ISTIOD_VERSION, MESH_METRICS, construct_metrics_config


class IstioCheckV2(OpenMetricsBaseCheckV2):

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(IstioCheckV2, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        self.scraper_configs = []
        mesh_endpoint = self.instance.get("istio_mesh_endpoint")
        istiod_endpoint = self.instance.get("istiod_endpoint")
        istiod_namespace = self.instance.get("namespace", ISTIOD_NAMESPACE)
        mesh_namespace = istiod_namespace + ".mesh"

        if not mesh_endpoint and not istiod_endpoint:
            raise ConfigurationError(
                "Must specify at least one of the following endpoints: `istio_mesh_endpoint` or `istiod_endpoint`."
            )

        if mesh_endpoint:
            self.scraper_configs.append(self._generate_config(mesh_endpoint, MESH_METRICS, mesh_namespace))
        if istiod_endpoint:
            self.scraper_configs.append(self._generate_config(istiod_endpoint, ISTIOD_METRICS, istiod_namespace))

    def _generate_config(self, endpoint, metrics, namespace):
        metrics = construct_metrics_config(metrics)
        metrics.append(ISTIOD_VERSION)
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': metrics,
            'namespace': namespace,
        }
        config.update(self.instance)
        return config

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

    def get_config_with_defaults(self, config):
        return ChainMap(config, {'metrics': config.pop('metrics'), 'namespace': config.pop('namespace')})
