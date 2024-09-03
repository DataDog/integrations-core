# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.octopus_deploy.config_models import ConfigMixin


class OctopusDeployCheck(AgentCheck, ConfigMixin):

    __NAMESPACE__ = 'octopus_deploy'

    def __init__(self, name, init_config, instances):
        super(OctopusDeployCheck, self).__init__(name, init_config, instances)

    def check(self, _):
        try:
            response = self.http.get(self.config.octopus_endpoint)
            response.raise_for_status()
        except (Timeout, HTTPError, InvalidURL, ConnectionError) as e:
            self.gauge("api.can_connect", 0, tags=self.config.tags)
            self.log.warning(
                "Failed to connect to Octopus Deploy endpoint %s: %s", self.config.octopus_endpoint, str(e)
            )
            raise

        self.gauge("api.can_connect", 1, tags=self.config.tags)
