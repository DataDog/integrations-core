# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import iteritems
import requests

from datadog_checks.base import AgentCheck

from . import common


class AmbariCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(AmbariCheck, self).__init__(name, init_config, agentConfig, instances)
        self.hosts = []
        self.clusters = []
        self.services = []

    def check(self, instance):
        server = instance.get("url", "")
        port = instance.get("port", "")
        tags = instance.get("tags", [])
        services = instance.get("services", [])
        headers = instance.get("metric_headers", [])
        clusters_endpoint = common.CLUSTERS_URL.format(ambari_server=server, ambari_port=port)
        cluster_list = self.get_clusters(clusters_endpoint)
        perform_service_check = True
        if instance.get("collect_host_metrics", True):
            self.get_host_metrics(cluster_list, server, port, tags)
            perform_service_check = False
        if instance.get("collect_service_metrics", True):
            self.get_service_metrics(cluster_list, server, port, services, headers, tags, perform_service_check)

    def get_clusters(self, url):
        cluster_list = []

        resp = self.make_request(url)

        if resp is None:
            self.warning(
                "Couldn't connect to URL: {}. Please verify the address is reachable"
                .format(url))
            self.submit_service_checks("can.connect", self.CRITICAL, ["url:{}".format(url)])
            raise

        self.submit_service_checks("can.connect", self.OK, ["url:{}".format(url)])
        clusters = resp.json()
        for cluster in clusters.get('items'):
            cluster_list.append(cluster.get('Clusters').get('cluster_name'))
        return cluster_list

    def get_host_metrics(self, clusters, server, port, tags):
        for cluster in clusters:
            hosts_endpoint = common.HOST_METRICS_URL.format(
                ambari_server=server,
                ambari_port=port,
                cluster_name=cluster
            )
            # resp = self.make_request("http://bad_endpoint.com") #for testing
            resp = self.make_request(hosts_endpoint)

            if resp is None:
                continue

            hosts_list = resp.get('items')
            cluster_tag = "ambari_cluster:{}".format(cluster)

            for host in hosts_list:
                metrics = self.host_metrics_iterate(host.get('metrics'), "")
                for metric_name, value in iteritems(metrics):
                    host_tag = "ambari_host:" + host.get('Hosts').get('host_name')
                    metric_tags = []
                    metric_tags += tags
                    metric_tags.extend((cluster_tag, host_tag))
                    if isinstance(value, float):
                        self.submit_metrics(metric_name, value, metric_tags)

    def get_service_metrics(self, clusters, server, port, services, headers, tags, perform_service_check):
        for cluster in clusters:
            for service, components in iteritems(services):
                components = [c.upper() for c in components]
                service_metrics_endpoint = common.SERVICE_METRICS_URL.format(
                    ambari_server=server,
                    ambari_port=port,
                    cluster_name=cluster,
                    service_name=service.upper()
                )

                resp = self.make_request(service_metrics_endpoint)
                # resp = self.make_request("http://bad_endpoint.com") #for testing
                cluster_tag = "ambari_cluster:{}".format(cluster)

                if resp is None:
                    continue

                self.submit_service_checks("can.connect", resp, ["url:{}".format(url)])

                for component in resp.get('items'):
                    component_name = component.get('ServiceComponentInfo').get('component_name')
                    if component_name in components:
                        for header in headers:
                            metrics = self.service_metrics_iterate(component.get('metrics')[header], header)
                            for metric_name, value in iteritems(metrics):
                                service_tag = "ambari_service:" + service.lower()
                                component_tag = "ambari_component:" + component_name.lower()
                                metric_tags = []
                                metric_tags += tags
                                metric_tags.extend((service_tag, component_tag, cluster_tag))

                                if isinstance(value, float):
                                    self.submit_metrics(metric_name, value, metric_tags)

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

    def submit_metrics(self, name, value, tags):
        self.gauge('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)

    def submit_service_checks(self, name, value, tags):
        self.service_check('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)
