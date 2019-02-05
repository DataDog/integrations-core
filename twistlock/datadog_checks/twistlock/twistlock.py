# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck

from .config import Config


class TwistlockCheck(OpenMetricsBaseCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):

        default_namespace = 'twistlock'

        super(TwistlockCheck, self).__init__(
            name,
            init_config,
            agentConfig,
            instances=instances,
            default_namespace=default_namespace
        )

    def check(self, instance):
        config = Config(instance)

        self.process(self.create_scraper_configuration(config.prometheus_instance))
