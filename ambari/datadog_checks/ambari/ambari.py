# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import iteritems
import requests
from xml.etree.ElementTree import ParseError

from datadog_checks.base import AgentCheck

from . import common


class AmbariCheck(AgentCheck):

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(AmbariCheck, self).__init__(name, init_config, agentConfig, instances)
        self.hosts = []
        self.clusters = []
        self.services = []

    def check(self, instance):
        server = instance.get("url")
        port = instance.get("port")
        tags = instance.get('tags', [])
        clusters_endpoint = common.CLUSTERS_URL.format(ambari_server=server, ambari_port=port)
        clusters = self.get_clusters(clusters_endpoint)
        self.get_host_metrics(clusters, server, port, tags)
        self.get_service_metrics(clusters, server, port, tags)

    def get_clusters(self, url):
        cluster_list = []
        try:
            resp = self.http.get(url)
            resp.raise_for_status()
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: {} with exception: {}. Please verify the address is reachable"
                .format(url, e))
            raise e
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
            try:
                # resp = self.make_request("http://bad_endpoint.com") #for testing
                resp = self.make_request(hosts_endpoint)
                hosts_list = resp.get('items')
                cluster_tag = "ambari_cluster:{}".format(cluster)
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
                hosts_list = []

            for host in hosts_list:
                metrics = self.metrics_iterate(host.get('metrics'), "")
                for metric_name, value in iteritems(metrics):
                    host_tag = "ambari_host:" + host.get('Hosts').get('host_name')
                    metric_tags = []
                    metric_tags += tags
                    metric_tags.extend((cluster_tag, host_tag))
                    if isinstance(value, float):
                        self.submit_metrics(metric_name, value, metric_tags)

    def get_service_metrics(self, clusters, server, port, tags):
        for cluster in clusters:
            services_endpoint = common.SERVICES_URL.format(
                ambari_server=server,
                ambari_port=port,
                cluster_name=cluster
            )
            services_list = []
            try:
                # resp = self.make_request("http://bad_endpoint.com") #for testing
                resp = self.make_request(services_endpoint)
                for service in resp.get('items'):
                    services_list.append(service.get('ServiceInfo').get('service_name'))
                cluster_tag = "ambari_cluster:{}".format(cluster)
            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
                # import pdb; pdb.set_trace()
                print e

            for service in services_list:
                service_metrics_endpoint = common.SERVICE_METRICS_URL.format(
                    ambari_server=server,
                    ambari_port=port,
                    cluster_name=cluster,
                    service_name=service
                )
                resp = self.make_request(service_metrics_endpoint)
                for component in resp.get('items'):
                    if component.get('metrics'):
                        metrics = self.metrics_iterate(component.get('metrics'), "")
                        for metric_name, value in iteritems(metrics):
                            component_name = component.get('ServiceComponentInfo').get('component_name')
                            service_tag = "ambari_service:" + service.lower()
                            component_tag = "ambari_component:" + component_name
                            metric_tags = []
                            metric_tags += tags
                            metric_tags.extend((service_tag, component_tag, cluster_tag))

                            if isinstance(value, float):
                                self.submit_metrics(metric_name, value, metric_tags)

    def metrics_iterate(self, metric_dict, prev_heading, prev_metrics={}):
        for key, value in iteritems(metric_dict):
            if key == "boottime":
                prev_metrics["boottime"] = value
            elif isinstance(value, dict):
                self.metrics_iterate(value, key, prev_metrics)
            else:
                prev_metrics['{}.{}'.format(prev_heading, key)] = value
        return prev_metrics

    def make_request(self, url):
        try:
            resp = self.http.get(url)
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            self.warning(
                "Couldn't connect to URL: {} with exception: {}. Please verify the address is reachable"
                .format(url, e))
            raise e
        return resp.json()

    def submit_metrics(self, name, value, tags):
        self.gauge('{}.{}'.format(common.METRIC_PREFIX, name), value, tags)
