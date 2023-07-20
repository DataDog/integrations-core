# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import cast

from datadog_checks.base import OpenMetricsBaseCheck

from .config import Config
from .types import Instance


class AzureIoTEdgeCheck(OpenMetricsBaseCheck):
    __NAMESPACE__ = 'azure.iot_edge'  # Child of `azure.` namespace.

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        self._config = Config(cast(Instance, instances[0]))
        super(AzureIoTEdgeCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={instance['prometheus_url']: instance for instance in self._config.prometheus_instances},
        )

    def check(self, _):
        for instance in self._config.prometheus_instances:
            scraper_config = self.get_scraper_config(instance)
            self.process(scraper_config)

    def get_scraper_config(self, instance):
        # This validation is called during `__init__` but we don't need it
        if 'prometheus_url' not in instance:
            return

        endpoint = instance['prometheus_url']

        if endpoint in self.config_map:
            return self.config_map[endpoint]

        config = self.create_scraper_configuration(instance)

        self.config_map[endpoint] = config

        return config
