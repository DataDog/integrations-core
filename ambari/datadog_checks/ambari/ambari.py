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

        base_url = "{}:{}{}".format(server, port, path)
        clusters = self.get_clusters(base_url)
        self.get_host_metrics(base_url, clusters, base_tags)
        self.get_service_metrics(base_url, clusters, services, metric_headers, base_tags)

    def get_clusters(self, base_url):
        clusters_endpoint = common.CLUSTERS_URL.format(base_url=base_url)

        resp = self.make_request(clusters_endpoint)
        if resp is None:
            self.submit_service_checks("can_connect", self.CRITICAL, ["url:{}".format(base_url)])
            raise CheckException("Couldn't connect to URL: {}. Please verify the address is reachable".format(clusters_endpoint))
        self.submit_service_checks("can_connect", self.OK, ["url:{}".format(base_url)])

        return [cluster.get('Clusters').get('cluster_name') for cluster in resp.get('items')]

    def get_host_metrics(self, base_url, clusters, base_tags):
        for cluster in clusters:
            hosts_endpoint = common.HOST_METRICS_URL.format(
                base_url=base_url,
                cluster_name=cluster
            )
            resp = self.make_request(hosts_endpoint)

            hosts_list = resp.get('items')
            cluster_tag = CLUSTER_TAG_TEMPLATE.format(cluster)

            for host in hosts_list:
                if host.get(METRICS_FIELD) is None:
                    self.log.warning("No metrics received for host {}".format(host.get('Hosts').get('host_name')))
                    continue

                metrics = self.flatten_host_metrics(host.get(METRICS_FIELD))
                for metric_name, value in iteritems(metrics):
                    host_tag = HOST_TAG + host.get('Hosts').get('host_name')
                    metric_tags = base_tags + [cluster_tag, host_tag]
                    if isinstance(value, float):
                        self.submit_gauge(metric_name, value, metric_tags)

    def get_service_metrics(self, base_url, clusters, services, metric_headers, base_tags):
        for cluster in clusters:
            tags = base_tags + [CLUSTER_TAG_TEMPLATE.format(cluster)]
            for service, components in iteritems(services):
                service_tag = SERVICE_TAG + service.lower()
                self.get_component_metrics(base_url, cluster, service, metric_headers,
                                           tags + [service_tag],
                                           [c.upper() for c in components])
                self.get_service_health(base_url, cluster, service, tags, service_tag)

    def get_service_health(self, base_url, cluster, service, base_tags, service_tag):
        service_check_endpoint = common.create_endpoint(base_url, cluster, service, SERVICE_INFO_QUERY)
        service_check_tags = base_tags + [service_tag]

        service_resp = self.make_request(service_check_endpoint)
        if service_resp is None:
            self.submit_service_checks("state", self.CRITICAL, service_check_tags)
            self.log.warning("No response received for service {}".format(service))
        else:
            state = service_resp.get('ServiceInfo').get('state')
            self.submit_service_checks("state", common.STATUS[state], service_check_tags)

    def get_component_metrics(self, base_url, cluster, service, metric_headers, base_tags, components):
        component_metrics_endpoint = common.create_endpoint(base_url, cluster, service, COMPONENT_METRICS_QUERY)
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
    def flatten_service_metrics(metric_dict, prefix):
        flat_metrics = {}
        for raw_metric_name, metric_value in iteritems(metric_dict):
            if isinstance(metric_value, dict):
                flat_metrics.update(AmbariCheck.flatten_service_metrics(metric_value, prefix))
            else:
                metric_name = '{}.{}'.format(prefix, raw_metric_name) if prefix else raw_metric_name
                flat_metrics[metric_name] = metric_value
        return flat_metrics

    @staticmethod
    def flatten_host_metrics(metric_dict, prefix=""):
        flat_metrics = {}
        for raw_metric_name, metric_value in iteritems(metric_dict):
            metric_name = '{}.{}'.format(prefix, raw_metric_name) if prefix else raw_metric_name
            if raw_metric_name == "boottime":
                flat_metrics["boottime"] = metric_value
            elif isinstance(metric_value, dict):
                flat_metrics.update(AmbariCheck.flatten_host_metrics(metric_value, metric_name))
            else:
                flat_metrics[metric_name] = metric_value
        return flat_metrics

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
