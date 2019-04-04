# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from six.moves.urllib.parse import quote, urljoin


CLUSTERS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters"
HOSTS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts/{host_name}"
HOST_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts/{host_name}"

class AmbariCheck(AgentCheck):
    # def __init__(self, name, init_config, agentConfig, instances=None):
    #     super(AmbariCheck, self).__init__(name, init_config, agentConfig, instances)
    #     self.hosts = []
    #     self.clusters = []
    #     self.services = []

    def check(self, instance):
        import pdb; pdb.set_trace()
        server = instance.get("url")
        port = instance.get("port")
        endpoint = CLUSTERS_URL.format(ambari_server=server, ambari_port=port)
        url = urljoin(server, endpoint)
        response = self.http.get(url).json()