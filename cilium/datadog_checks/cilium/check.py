# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .metrics import AGENT_V2_METRICS, OPERATOR_V2_METRICS, construct_metrics_config

CILIUM_VERSION = {'cilium_version': {'type': 'metadata', 'label': 'version', 'name': 'version'}}


class CiliumCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'cilium'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        self.scraper_configs = []
        agent_endpoint = self.instance.get("agent_endpoint")
        operator_endpoint = self.instance.get("operator_endpoint")
        if not agent_endpoint and not operator_endpoint:
            raise ConfigurationError(
                "Must specify at least one of the following endpoints: `agent_endpoint` or `operator_endpoint`."
            )

        if agent_endpoint:
            self.scraper_configs.append(self._generate_config(agent_endpoint, AGENT_V2_METRICS))
        if operator_endpoint:
            self.scraper_configs.append(self._generate_config(operator_endpoint, OPERATOR_V2_METRICS))

    def _generate_config(self, endpoint, metrics):
        metrics = construct_metrics_config(metrics)
        metrics.append(CILIUM_VERSION)
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': metrics,
        }
        config.update(self.instance)
        return config

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

    def get_config_with_defaults(self, config):
        return ChainMap(config, {'metrics': config.pop('metrics')})
