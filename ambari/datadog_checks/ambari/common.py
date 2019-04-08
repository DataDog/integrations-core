# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

CLUSTERS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters"
HOSTS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts/{host_name}"
HOST_METRICS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/hosts?fields=metrics"
SERVICES_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/services"
SERVICE_METRICS_URL = "http://{ambari_server}:{ambari_port}/api/v1/clusters/{cluster_name}/services/{service_name}/components?fields=metrics" # noqa E501
METRIC_PREFIX = 'ambari'
