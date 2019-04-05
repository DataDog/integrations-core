# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

CLUSTERS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters"
HOST_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts/{host_name}"
HOSTS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts?fields=metrics"
SERVICES_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/services?fields=metrics"
METRIC_PREFIX = 'ambari'
