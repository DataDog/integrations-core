# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import iteritems
import requests


from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException
from . import common

# Tag templates
CLUSTER_TAG_TEMPLATE = "ambari_cluster:{}"
HOST_TAG = "ambari_host:"
SERVICE_TAG = "ambari_service:"
COMPONENT_TAG = "ambari_component:"

# URL queries
COMPONENT_METRICS_QUERY = "/components?fields=metrics"
SERVICE_INFO_QUERY = "?fields=ServiceInfo"

# Response fields
METRICS_FIELD = "metrics"


class AmbariCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(AmbariCheck, self).__init__(name, init_config, agentConfig, instances)
        self.hosts = []
        self.clusters = []
        self.services = []

    def check(self, instance):
        server = instance.get("url", "")
        port = str(instance.get("port", ""))
        tags = instance.get("tags", [])
        services = instance.get("services", [])
        headers = instance.get("metric_headers", [])
        headers = [str(h) for h in headers]

        cluster_list = self.get_clusters(server, port)
        self.get_host_metrics(cluster_list, server, port, tags)
        self.get_service_metrics(cluster_list, server, port, services, headers, tags)

    def get_clusters(self, server, port):
        clusters_endpoint = common.CLUSTERS_URL.format(ambari_server=server, ambari_port=port)

        resp = self.make_request(clusters_endpoint)
        if resp is None:
            self.submit_service_checks("can_connect", self.CRITICAL, ["url:{}".format(server)])
            raise CheckException("Couldn't connect to URL: {}. Please verify the address is reachable".format(clusters_endpoint))
        self.submit_service_checks("can_connect", self.OK, ["url:{}".format(server)])

        return [cluster.get('Clusters').get('cluster_name') for cluster in resp.get('items')]

    def get_host_metrics(self, clusters, server, port, tags):
        for cluster in clusters:
            hosts_endpoint = common.HOST_METRICS_URL.format(
                ambari_server=server,
                ambari_port=port,
                cluster_name=cluster
            )
            resp = self.make_request(hosts_endpoint)

            hosts_list = resp.get('items')
            cluster_tag = CLUSTER_TAG_TEMPLATE.format(cluster)

            for host in hosts_list:
                if host.get(METRICS_FIELD) is None:
                    self.log.warning("No metrics received for host {}".format(host.get('Hosts').get('host_name')))
                    continue

                metrics = self.host_metrics_iterate(host.get(METRICS_FIELD), "")
                for metric_name, value in iteritems(metrics):
                    host_tag = HOST_TAG + host.get('Hosts').get('host_name')
                    metric_tags = []
                    metric_tags += tags
                    metric_tags.extend((cluster_tag, host_tag))
                    if isinstance(value, float):
                        self.submit_metrics(metric_name, value, metric_tags)

    def get_service_metrics(self, clusters, server, port, services, headers, tags):
        for cluster in clusters:
            cluster_tag = CLUSTER_TAG_TEMPLATE.format(cluster)
            for service, components in iteritems(services):
                components = [c.upper() for c in components]
                metrics_endpoint = create_endpoint(server, port, cluster, service, COMPONENT_METRICS_QUERY)
                service_check_endpoint = create_endpoint(server, port, cluster, service, SERVICE_INFO_QUERY)

                resp = self.make_request(metrics_endpoint)
                # resp = self.make_request("http://bad_endpoint.com") #for testing
                service_tag = SERVICE_TAG + service.lower()

                if resp is None:
                    self.log.warning("No components found for service {}.".format(service))
                    continue

                for component in resp.get('items'):
                    component_name = component.get('ServiceComponentInfo').get('component_name')
                    component_tag = COMPONENT_TAG + component_name.lower()

                    if component_name not in components:
                        continue
                    if component.get(METRICS_FIELD) is None:
                        self.log.warning(
                            "No metrics found for component {} for service {}"
                            .format(component_name, service)
                        )
                        continue

                    for header in headers:
                        if header not in component.get(METRICS_FIELD):
                            self.log.warning(
                                "No {} metrics found for component {} for service {}"
                                .format(header, component_name, service)
                            )
                            continue

                        metrics = self.service_metrics_iterate(component.get(METRICS_FIELD)[header], header)
                        for metric_name, value in iteritems(metrics):
                            metric_tags = []
                            metric_tags += tags
                            metric_tags.extend((service_tag, component_tag, cluster_tag))

                            if isinstance(value, float):
                                self.submit_metrics(metric_name, value, metric_tags)

                # service health check
                service_resp = self.make_request(service_check_endpoint)
                service_check_tags = tags.copy()
                service_check_tags.extend((service_tag, cluster_tag))
                if service_resp is None:
                    self.submit_service_checks("state", self.CRITICAL, service_check_tags)
                    self.log.warning("No response received for service {}".format(service))
                else:
                    state = service_resp.get('ServiceInfo').get('state')
                    self.submit_service_checks("state", common.STATUS[state], service_check_tags)

    @staticmethod
    def create_endpoint(server, port, cluster, service, ending):
        return common.SERVICE_URL.format(
                    ambari_server=server,
                    ambari_port=port,
                    cluster_name=cluster,
                    service_name=service.upper(),
                    ending=ending
        )

    def service_metrics_iterate(self, metric_dict, header, prev_metrics={}):
        for key, value in iteritems(metric_dict):
            if isinstance(value, dict):
                self.service_metrics_iterate(value, header, prev_metrics)
            else:
                prev_metrics['{}.{}'.format(header, key)] = value
        return prev_metrics

    def host_metrics_iterate(self, metric_dict, prev_heading, prev_metrics={}):
        for key, value in iteritems(metric_dict):
            if key == "boottime":
                prev_metrics["boottime"] = value
            elif isinstance(value, dict):
                self.host_metrics_iterate(value, key, prev_metrics)
            else:
                prev_metrics['{}.{}'.format(prev_heading, key)] = value
        return prev_metrics

    def make_request(self, url):
        try:
            resp = self.http.get(url)
            return resp.json()
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: {} with exception: {}. Please verify the address is reachable"
                .format(url, e))
        except requests.exceptions.Timeout:
            self.warning("Connection timeout when connecting to {}".format(url))

    def submit_metrics(self, name, value, tags):
        self.gauge('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)

    def submit_service_checks(self, name, value, tags):
        self.service_check('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)
