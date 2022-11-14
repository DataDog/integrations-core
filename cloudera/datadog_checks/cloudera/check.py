# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import time

from datadog_checks.base import AgentCheck

from .client_factory import make_api_client


class ClouderaCheck(AgentCheck):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        super(ClouderaCheck, self).__init__(name, init_config, instances)

        self.client, self._error = make_api_client(self, self.instance)
        if self.client is None:
            self.error("API Client is none: %s", self._error)
            self.service_check("can_connect", ClouderaCheck.CRITICAL)

    def run_timeseries_checks(self):
        to_time = datetime.datetime.fromtimestamp(time.time())
        from_time = datetime.datetime.fromtimestamp(time.time() - 1000)
        query = "select last(cpu_soft_irq_rate)"
        response = self.client.query_time_series(query=query, from_time=from_time, to_time=to_time)

        for entry in response:
            value = entry.data[0].value
            attributes = entry.metadata.attributes
            tags = [
                f'cloudera_hostname:{attributes["hostname"]}',
                f'cluster_display_name:{attributes["clusterDisplayName"]}',
                f'entity_name:{attributes["entityName"]}',
                f'cluster_name:{attributes["clusterName"]}',
                f'host_id:{attributes["hostId"]}',
                f'category:{attributes["category"]}',
                f'rack_id:{attributes["rackId"]}',
            ]
            self.gauge("host.cpu_soft_irq_rate", value, tags=tags)

    def run_service_checks(self):
        self.service_check("can_connect", ClouderaCheck.OK)


    def check(self, _):
        # Run through the list of default timeseries metrics first
        self.run_timeseries_checks()

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
        self.run_service_checks()


        # Run any custom queries

        # at the end, output can_connect