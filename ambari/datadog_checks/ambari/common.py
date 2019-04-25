# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.constants import ServiceCheck

CLUSTERS_URL = "{base_url}/api/v1/clusters"
HOSTS_URL = "{base_url}/api/v1/clusters/{cluster_name}/hosts/{host_name}"
HOST_METRICS_URL = "{base_url}/api/v1/clusters/{cluster_name}/hosts?fields=metrics"
SERVICE_URL = "{base_url}/api/v1/clusters/{cluster_name}/services/{service_name}{ending}"
METRIC_PREFIX = 'ambari'

# https://github.com/apache/ambari/blob/trunk/ambari-server/docs/api/v1/service-resources.md
STATUS = {
    'INIT': ServiceCheck.OK,
    'INSTALLING': ServiceCheck.OK,
    'INSTALLED': ServiceCheck.OK,
    'STARTING': ServiceCheck.OK,
    'STARTED': ServiceCheck.OK,
    'STOPPING':	ServiceCheck.WARNING,
    'UNINSTALLING': ServiceCheck.WARNING,
    'UPGRADING': ServiceCheck.WARNING,
    'MAINTENANCE': ServiceCheck.WARNING,
    'INSTALL_FAILED': ServiceCheck.CRITICAL,
    'UNINSTALLED': ServiceCheck.CRITICAL,
    'WIPING_OUT': ServiceCheck.CRITICAL,
    'UNKNOWN': ServiceCheck.UNKNOWN
}


def create_endpoint(base_url, cluster, service, ending):
    return SERVICE_URL.format(
                base_url=base_url,
                cluster_name=cluster,
                service_name=service.upper(),
                ending=ending
    )
