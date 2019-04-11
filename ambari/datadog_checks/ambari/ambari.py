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
        cluster_list = self.get_clusters(clusters_endpoint, server)
        self.get_host_metrics(cluster_list, server, port, tags)
        self.get_service_metrics(cluster_list, server, port, services, headers, tags)

    def get_clusters(self, cluster_url, base_url):
        cluster_list = []

        resp = self.make_request(cluster_url)

        if resp is None:
            self.warning(
                "Couldn't connect to URL: {}. Please verify the address is reachable"
                .format(cluster_url))
            self.submit_service_checks("can_connect", self.CRITICAL, ["url:{}".format(base_url)])
            raise

        self.submit_service_checks("can_connect", self.OK, ["url:{}".format(base_url)])
        for cluster in resp.get('items'):
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

            if resp.get('metrics') is None:
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

    def get_service_metrics(self, clusters, server, port, services, headers, tags):
        for cluster in clusters:
            cluster_tag = "ambari_cluster:{}".format(cluster)
            for service, components in iteritems(services):
                components = [c.upper() for c in components]
                metrics_endpoint = self.create_endpoint(server, port, cluster, service, "/components?fields=metrics")
                service_check_endpoint = self.create_endpoint(server, port, cluster, service, "?fields=ServiceInfo")
                resp = self.make_request(metrics_endpoint)
                # resp = self.make_request("http://bad_endpoint.com") #for testing
                service_tag = "ambari_service:" + service.lower()

                if resp.get('items') is None:
                    continue

                for component in resp.get('items'):
                    component_name = component.get('ServiceComponentInfo').get('component_name')
                    component_tag = "ambari_component:" + component_name.lower()
                    if component_name in components:
                        for header in headers:
                            if (component.get('metrics') is not None) and (header in component.get('metrics')):
                                metrics = self.service_metrics_iterate(component.get('metrics')[header], header)
                                for metric_name, value in iteritems(metrics):
                                    metric_tags = []
                                    metric_tags += tags
                                    metric_tags.extend((service_tag, component_tag, cluster_tag))

                                    if isinstance(value, float):
                                        self.submit_metrics(metric_name, value, metric_tags)
                service_resp = self.make_request(service_check_endpoint)

                service_check_tags = []
                service_check_tags += tags
                service_check_tags.extend((service_tag, cluster_tag))
                if service_resp is None:
                    self.submit_service_checks("state", self.CRITICAL, service_check_tags)
                else:
                    state = service_resp.get('ServiceInfo').get('state')
                    self.submit_service_checks("state", common.STATUS[state], service_check_tags)
                    self.log.debug(state)

    def create_endpoint(self, server, port, cluster, service, ending):
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

    def submit_metrics(self, name, value, tags):
        self.gauge('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)

    def submit_service_checks(self, name, value, tags):
        self.service_check('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)
