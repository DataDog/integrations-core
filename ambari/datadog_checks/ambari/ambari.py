# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import iteritems

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
        tags = []
        clusters_endpoint = common.CLUSTERS_URL.format(ambari_server=server, ambari_port=port)
        clusters = self.get_clusters(clusters_endpoint)
        self.get_hosts_metrics(clusters, server, port, tags)

    def get_clusters(self, url):
        cluster_list = []
        r = self.http.get(url)
        r.raise_for_status()

        clusters = r.json().get('items')
        for cluster in clusters:
            cluster_list.append(cluster.get('Clusters').get('cluster_name'))
        return cluster_list

    def get_hosts_metrics(self, clusters, server, port, tags):
        for cluster in clusters:
            hosts_endpoint = common.HOSTS_URL.format(ambari_server=server, ambari_port=port, cluster_name=cluster)
            resp = self.http.get(hosts_endpoint)
            resp.raise_for_status()
            hosts_list = resp.json().get('items')
            cluster_tag = "ambari_cluster:{}".format(cluster)

            for host in hosts_list:
                metrics = self.host_iterate(host.get('metrics'), "")
                for metric_name, value in iteritems(metrics):
                    host_tags = [cluster_tag, "ambari_host:" + host.get('Hosts').get('host_name')]
                    self.submit_metrics(metric_name, value, host_tags)

    # def get_service_metrics(self, clusters, server, port):
    #     for cluster in clusters:
    #         services_endpoint = common.SERVICES_URL.format(
    #                                                        ambari_server=server,
    #                                                        ambari_port=port,
    #                                                        cluster_name=cluster
    #         )
    #         resp = self.http.get(services_endpoint)
    #         resp.raise_for_status()
    #         services_list = resp.json().get('items')
    #         cluster_tag = "ambari_cluster:{}".format(cluster)

    #         for service in services_list:
    #             service_tags = [
    #                             cluster_tag,
    #                             "ambari_host:" + service.get('Hosts').get('host_name'),
    #                             "ambari_server:" + service.get('Services').get('service_name')
    #             ]
    #             self.submit_metrics("test.value", service.get('metrics').get('cpu').get('cpu_idle'), service_tags)

    def host_iterate(self, metric_dict, prev_heading, prev_metrics={}):
        for key, value in iteritems(metric_dict):
            if key == "boottime":
                prev_metrics["boottime"] = value
            elif isinstance(value, dict):
                self.host_iterate(value, key, prev_metrics)
            else:
                prev_metrics['{}.{}'.format(prev_heading, key)] = value
        return prev_metrics

    def submit_metrics(self, name, value, tags):
        # value = child.get(metrics.METRIC_VALUE_FIELDS[child.tag])
        # metric_name = self.normalize(
        #     ensure_unicode(child.get('name')),
        #     prefix='{}.{}'.format(self.METRIC_PREFIX, prefix),
        #     fix_case=True
        # )
        # self.metric_type_mapping[child.tag](metric_name, value, tags=tags)
        self.gauge(name, value, tags)
