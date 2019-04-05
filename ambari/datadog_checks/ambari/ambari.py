# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

CLUSTERS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters"
HOST_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts/{host_name}"
HOSTS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts?fields=metrics"
SERVICES_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/services"


class AmbariCheck(AgentCheck):
    METRIC_PREFIX = 'ambari'

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(AmbariCheck, self).__init__(name, init_config, agentConfig, instances)
        self.hosts = []
        self.clusters = []
        self.services = []

        # use as template from ibm_was check
        # self.metric_type_mapping = {
        #     'AverageStatistic': self.gauge,
        #     'BoundedRangeStatistic': self.gauge,
        #     'CountStatistic': self.monotonic_count,
        #     'DoubleStatistic': self.rate,
        #     'RangeStatistic': self.gauge,
        #     'TimeStatistic': self.gauge
        # }

    def check(self, instance):
        server = instance.get("url")
        port = instance.get("port")
        tags = []
        clusters_endpoint = CLUSTERS_URL.format(ambari_server=server, ambari_port=port)

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
            hosts_endpoint = HOSTS_URL.format(ambari_server=server, ambari_port=port, cluster_name=cluster)
            resp = self.http.get(hosts_endpoint)
            resp.raise_for_status()
            hosts_list = resp.json().get('items')
            cluster_tag = "ambari_cluster:{}".format(cluster)

            for host in hosts_list:
                import pdb;
                pdb.set_trace()
                host_tags = [cluster_tag, "ambari_host:" + host.get('Hosts').get('host_name')]
                self.submit_metrics("test.value", host.get('metrics').get('cpu').get('cpu_idle'), host_tags)

    # def get_service_metrics(self, clusters, server, port):
    #     service_list = []

    #     services_endpoint = SERVICES_URL.format(ambari_server=server, ambari_port=port, cluster_name=cluster)

    #         try:
    #             service_response = self.http.get(services_endpoint)
    #             service_response.raise_for_status()
    #         except:
    #             raise

    #     services = service_response.json().get('items')
    #     for service in services:
    #         hosts_and_services_list["service_list"].append(service.get('ServiceInfo').get('service_name'))

    #     return service_list

    def submit_metrics(self, name, value, tags):
        # value = child.get(metrics.METRIC_VALUE_FIELDS[child.tag])
        # metric_name = self.normalize(
        #     ensure_unicode(child.get('name')),
        #     prefix='{}.{}'.format(self.METRIC_PREFIX, prefix),
        #     fix_case=True
        # )
        # self.metric_type_mapping[child.tag](metric_name, value, tags=tags)
        import pdb
        pdb.set_trace()
        self.gauge(name, value, tags)
