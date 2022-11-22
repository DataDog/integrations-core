# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError

from .client_factory import make_api_client
from .common import (
    API_ENTITY_STATUS,
    CAN_CONNECT,
    CLUSTER_HEALTH,
    CLUSTERS_RESOURCE_API,
    HOST_HEALTH,
    ROLE_HEALTH,
    SERVICES_RESOURCE_API,
)
from .queries import TIMESERIES_QUERIES


class ClouderaCheck(AgentCheck):
    __NAMESPACE__ = 'cloudera'

    def __init__(self, name, init_config, instances):
        if PY2:
            raise ConfigurationError(
                "This version of the integration is only available when using py3. "
                "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                "for more information."
            )

        super(ClouderaCheck, self).__init__(name, init_config, instances)

        self.client, self._error = make_api_client(self, self.instance)
        if self.client is None:
            self.log.error(f"Cloudera API Client is none: {self._error}")
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL)

        self.custom_tags = self.instance.get("tags", [])

    def run_timeseries_checks(self):
        # For each timeseries query, get the metrics
        # TODO: Running these metrics cause the execution time to be high, run async?
        for query in TIMESERIES_QUERIES:
            items = self.client.run_timeseries_query(query=query['query_string'])
            for item in items:
                if not item.data:
                    self.log.debug(f"Data for entity {item.metadata.entity_name} is empty")
                    continue

                value = item.data[0].value
                attributes = item.metadata.attributes

                # TODO: Add custom tags to this
                tags = []
                for datadog_tag, attribute in query['tags']:
                    try:
                        tags.append(f"{datadog_tag}:{attributes[attribute]}")
                    except:
                        self.log.debug(f"no {datadog_tag} tag for metric {item.metadata.entity_name}")

                category = attributes['category'].lower()
                self.gauge(f"{category}.{query['metric_name']}", value, tags=tags)

    def run_service_checks(self):
        # Structure:
        # Cluster
        # - Service
        #   - Nameservice
        #   - Role
        # - Host

        cluster_responses = self.client.run_query(
            CLUSTERS_RESOURCE_API, "read_clusters", view='full', cluster_type='any'
        )
        for cluster_response in cluster_responses:
            tags = [
                f'cluster_type:{cluster_response.cluster_type}',
                f'cluster_url:{cluster_response.cluster_url}',
                f'cluster_name:{cluster_response.display_name}',
            ]
            self._submit_health_check(cluster_response, CLUSTER_HEALTH, tags)

            # For each cluster, get the services
            service_responses = self.client.run_query(
                SERVICES_RESOURCE_API, "read_services", view='full', cluster_name=cluster_response.display_name
            )

            for service_response in service_responses:
                tags = [
                    f'service_name:{service_response.display_name}',
                    f'service_url:{service_response.service_url}',
                    f'service_url:{service_response.service_url}',
                    f'service_type:{service_response.type}',
                ]
                # role and services are the same, but since the metric categories use role, the service check will use role as well
                self._submit_health_check(service_response, ROLE_HEALTH, tags)

                # TODO: Get nameservice and role health checks

            # For each cluster, get the hosts
            host_responses = self.client.run_query(
                CLUSTERS_RESOURCE_API, "list_hosts", view='full', cluster_name=cluster_response.display_name
            )

            for host_response in host_responses:
                host_tags = [
                    f'cloudera_host_id:{host_response.host_id}',
                    f'cloudera_host_url:{host_response.host_url}',
                    f'cloudera_hostname:{host_response.hostname}',
                ]
                self._submit_health_check(host_response, HOST_HEALTH, host_tags)
                # submit metrics for hosts
                self.gauge("host.num_cores", host_response.num_cores, host_tags)
                self.gauge("host.num_physical_cores", host_response.num_physical_cores, host_tags)
                self.gauge("host.total_phys_mem_bytes", host_response.total_phys_mem_bytes, host_tags)

        # host metrics

        # Output OK can_connect if got to here
        self.service_check(CAN_CONNECT, AgentCheck.OK)

    def _submit_health_check(self, item, service_check, tags):
        status = API_ENTITY_STATUS[item.entity_status]
        message = None if status is AgentCheck.OK else item.entity_status

        self.service_check(service_check, status, message=message, tags=tags)

    def check(self, _):
        # Run through the list of default timeseries metrics first
        self.run_timeseries_checks()

        # Get the service checks of cluster, service, nameservice, role, and host
        self.run_service_checks()

        # Get the health check metrics of clusters and services

        # TODO: Run any custom queries
