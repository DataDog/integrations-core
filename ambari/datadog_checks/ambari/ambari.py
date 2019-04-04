# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from six.moves.urllib.parse import quote, urljoin


CLUSTERS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters"
HOSTS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts"
SERVICES_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/services"

class AmbariCheck(AgentCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(AmbariCheck, self).__init__(name, init_config, agentConfig, instances)
        self.hosts = []
        self.clusters = []
        self.services = []

    def check(self, instance):
        server = instance.get("url")
        port = instance.get("port")
        clusters_endpoint = CLUSTERS_URL.format(ambari_server=server, ambari_port=port)

        clusters = self.get_clusters(clusters_endpoint)
        hosts_and_services = self.get_hosts_and_services(clusters, server, port)
        hosts = hosts_and_services["host_list"]
        services = hosts_and_services["service_list"]
        import pdb; pdb.set_trace()

        
    def get_clusters(self, url):
        cluster_list = []
        try:
            r = self.http.get(url)
            r.raise_for_status()
        except:
            raise

        clusters = r.json().get('items')
        for cluster in clusters:
            cluster_list.append(cluster.get('Clusters').get('cluster_name'))
        return cluster_list

    def get_hosts_and_services(self, clusters, server, port):
        hosts_and_services_list = {
            "host_list": [],
            "service_list": []
        }
        for cluster in clusters:
            hosts_endpoint = HOSTS_URL.format(ambari_server=server, ambari_port=port, cluster_name=cluster)
            services_endpoint = SERVICES_URL.format(ambari_server=server, ambari_port=port, cluster_name=cluster)

            try:
                host_response = self.http.get(hosts_endpoint)
                host_response.raise_for_status()
            except:
                raise

            try:
                service_response = self.http.get(services_endpoint)
                service_response.raise_for_status()
            except:
                raise

        hosts = host_response.json().get('items')
        services = service_response.json().get('items')
        for host in hosts:
            hosts_and_services_list["host_list"].append(host.get('Hosts').get('host_name'))
        for service in services:
            hosts_and_services_list["service_list"].append(service.get('ServiceInfo').get('service_name'))
        return hosts_and_services_list