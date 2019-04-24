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
        path = str(instance.get("path", ""))
        base_tags = instance.get("tags", [])
        services = instance.get("services", [])
        metric_headers = [str(h) for h in instance.get("metric_headers", [])]

        clusters = self.get_clusters(server, port)
        self.get_host_metrics(clusters, server, port, base_tags)
        self.get_service_metrics(clusters, server, port, services, metric_headers, base_tags)

    def get_clusters(self, server, port):
        clusters_endpoint = common.CLUSTERS_URL.format(ambari_server=server, ambari_port=port)

        resp = self.make_request(clusters_endpoint)
        if resp is None:
            self.submit_service_checks("can_connect", self.CRITICAL, ["url:{}".format(server)])
            raise CheckException("Couldn't connect to URL: {}. Please verify the address is reachable".format(clusters_endpoint))
        self.submit_service_checks("can_connect", self.OK, ["url:{}".format(server)])

        return [cluster.get('Clusters').get('cluster_name') for cluster in resp.get('items')]

    def get_host_metrics(self, clusters, server, port, base_tags):
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

                metrics = self.flatten_host_metrics(host.get(METRICS_FIELD), "")
                for metric_name, value in iteritems(metrics):
                    host_tag = HOST_TAG + host.get('Hosts').get('host_name')
                    metric_tags = base_tags + [cluster_tag, host_tag]
                    if isinstance(value, float):
                        self.submit_gauge(metric_name, value, metric_tags)

    def get_service_metrics(self, clusters, server, port, services, metric_headers, base_tags):
        for cluster in clusters:
            tags = base_tags + [CLUSTER_TAG_TEMPLATE.format(cluster)]
            for service, components in iteritems(services):
                service_tag = SERVICE_TAG + service.lower()
                self.get_component_metrics(server, port, cluster, service, metric_headers,
                                           tags + [service_tag],
                                           [c.upper() for c in components])
                self.get_service_health(cluster, server, port, service, tags, service_tag)

    def get_service_health(self, cluster, server, port, service, base_tags, service_tag):
        service_check_endpoint = common.create_endpoint(server, port, cluster, service, SERVICE_INFO_QUERY)
        service_check_tags = base_tags + [service_tag]

        service_resp = self.make_request(service_check_endpoint)
        if service_resp is None:
            self.submit_service_checks("state", self.CRITICAL, service_check_tags)
            self.log.warning("No response received for service {}".format(service))
        else:
            state = service_resp.get('ServiceInfo').get('state')
            self.submit_service_checks("state", common.STATUS[state], service_check_tags)

    def get_component_metrics(self, server, port, cluster, service, metric_headers, base_tags, components):
        component_metrics_endpoint = common.create_endpoint(server, port, cluster, service, COMPONENT_METRICS_QUERY)
        resp = self.make_request(component_metrics_endpoint)

        if resp is None:
            self.log.warning("No components found for service {}.".format(service))
            return

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

            for header in metric_headers:
                if header not in component.get(METRICS_FIELD):
                    self.log.warning(
                        "No {} metrics found for component {} for service {}"
                            .format(header, component_name, service)
                    )
                    continue

                metrics = self.flatten_service_metrics(component.get(METRICS_FIELD)[header], header)
                for metric_name, value in iteritems(metrics):
                    metric_tags = base_tags + [component_tag]
                    if isinstance(value, float):
                        self.submit_gauge(metric_name, value, metric_tags)
                    else:
                        self.log.warning("Expected a float for {}, received {}".format(metric_name, value))

    @staticmethod
    def flatten_service_metrics(metric_dict, prefix, flat_metrics=None):
        flat_metrics = flat_metrics or {}
        for key, value in iteritems(metric_dict):
            if isinstance(value, dict):
                AmbariCheck.flatten_service_metrics(value, prefix, flat_metrics)
            else:
                flat_metrics['{}.{}'.format(prefix, key)] = value
        return flat_metrics

    @staticmethod
    def flatten_host_metrics(metric_dict, prev_heading, prev_metrics=None):
        prev_metrics = prev_metrics or {}
        for key, value in iteritems(metric_dict):
            if key == "boottime":
                prev_metrics["boottime"] = value
            elif isinstance(value, dict):
                AmbariCheck.flatten_host_metrics(value, key, prev_metrics)
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

    def submit_gauge(self, name, value, tags):
        self.gauge('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)

    def submit_service_checks(self, name, value, tags):
        self.service_check('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)
