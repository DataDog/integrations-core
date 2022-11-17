# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import time

from datadog_checks.base import AgentCheck

from .client_factory import make_api_client
from .common import API_ENTITY_STATUS, CAN_CONNECT, CLUSTER_HEALTH, CLUSTER_RESOURCE_API, SERVICE_HEALTH, SERVICE_RESOURCE_API
from .queries import TIMESERIES_QUERIES


class ClouderaCheck(AgentCheck):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        super(ClouderaCheck, self).__init__(name, init_config, instances)

        self.client, self._error = make_api_client(self, self.instance)
        if self.client is None:
            self.error("API Client is none: %s", self._error)
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL)

        self.custom_tags = self.instance.get("tags", [])

    def run_timeseries_checks(self):
        to_time = datetime.datetime.fromtimestamp(time.time())
        from_time = datetime.datetime.fromtimestamp(time.time() - 6000)

        # For each timeseries query, get the metrics
        for query in TIMESERIES_QUERIES:
            items = self.client.run_timeseries_query(query=query['query_string'], from_time=from_time, to_time=to_time)

            for item in items.time_series:
                value = item.data[0].value
                attributes = item.metadata.attributes

                # TODO: make this compatible with Py2
                tags = [f"{datadog_tag}:{attributes[attribute]}" for datadog_tag, attribute in query['tags']]

                category = attributes['category'].lower()
                self.gauge(f"{category}.{query['metric_name']}", value, tags=tags)


    def run_service_checks(self):
        # Structure:
        # Cluster
        # - Service
        #   - Nameservice
        #   - Role
        # - Host

        cluster_responses = self.client.run_query(CLUSTER_RESOURCE_API, "read_clusters", view='full', cluster_type='any')
        for cluster_response in cluster_responses:
            tags = [
                f'cluster_type:{cluster_response.cluster_type}',
                f'cluster_url:{cluster_response.cluster_url}',
                f'cluster_name:{cluster_response.display_name}',
            ]
            self._submit_health_check(cluster_response, CLUSTER_HEALTH,  tags)
            
            # For each cluster, get the services
            services = self.client.run_query(SERVICE_RESOURCE_API, "read_services", view='full', cluster_name=cluster_response.display_name)

            for service in services:
                tags = [
                    f'service_name:{service.display_name}',
                    f'service_url:{service.service_url}',
                    f'service_url:{service.service_url}',
                    f'service_type:{service.type}',
                ]
                self._submit_health_check(service, SERVICE_HEALTH,  tags)

                # TODO: Get nameservice and role health checks

        # TODO: Get host health check

        # Output OK can_connect if got to here
        self.service_check(CAN_CONNECT, AgentCheck.OK)

    def _submit_service_check(self, item, service_check, tags):
        status = API_ENTITY_STATUS[item.entity_status]
        message = None if status is AgentCheck.OK else item.entity_status
        
        self.service_check(service_check, status, message=message, tags=tags)

    def check(self, _):
        # Run through the list of default timeseries metrics first
        self.run_timeseries_checks()

        # Get the service checks of cluster, service, nameservice, role, and host
        self.run_service_checks()

        # TODO: Run any custom queries
