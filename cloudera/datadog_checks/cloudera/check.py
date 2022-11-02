# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import AgentCheck

from .client_factory import make_api_client


class ClouderaCheck(AgentCheck):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        super(ClouderaCheck, self).__init__(name, init_config, instances)

        self.client, self._error = make_api_client(self, self.instance)
        if self.client is None:
            self.log.error("API Client is none: %s", self._error)
            self.service_check("can_connect", ClouderaCheck.CRITICAL)

    def check(self, _):
        # Run through the list of default metrics first

        # Get the clusters
        # ClustersResourceApi

        # For each cluster, get the services
        # ServicesResourceApi

        # Structure:
        # Cluster
        # - Service
        #   - Nameservice
        #   - Role
        # - Host

        # Get host metrics
        # HostsResourceApi

        # get nameservice metrics
        # NameservicesResourceApi

        # get role metrics
        # RolesResourceApi

        # get service metrics
        # ServicesResourceApi

        # Next steps: try to get cluster metrics and see how to structure hierarchy


        # Run any custom queries

        # at the end, output can_connect
        self.service_check("can_connect", ClouderaCheck.OK)
