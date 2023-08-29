# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

from copy import deepcopy

from kubeutil import get_connection_info

METRIC_TYPES = ['counter', 'gauge', 'summary']

# container-specific metrics should have all these labels
PRE_1_16_CONTAINER_LABELS = {'namespace', 'name', 'image', 'id', 'container_name', 'pod_name'}
POST_1_16_CONTAINER_LABELS = {'namespace', 'name', 'image', 'id', 'container', 'pod'}

# Value above which the figure can be discarded because it's an aberrant transient value
MAX_MEMORY_RSS = 2**63

SLI_METRICS_PATH = '/metrics/slis'


class SliMetricsScraperMixin(object):
    """
    This class scrapes metrics for the kube scheduler "/metrics/sli" prometheus endpoint and submits
    them on behalf of a check.
    """

    def __init__(self, *args, **kwargs):
        super(SliMetricsScraperMixin, self).__init__(*args, **kwargs)

        # these are filled by container_<metric-name>_usage_<metric-unit>
        # and container_<metric-name>_limit_<metric-unit> reads it to compute <metric-name>usage_pct
        self.fs_usage_bytes = {}
        self.mem_usage_bytes = {}
        self.swap_usage_bytes = {}

        self.SLI_METRIC_TRANSFORMERS = {
            # 'container_cpu_usage_seconds_total': self.container_cpu_usage_seconds_total,
        }

    def _create_sli_prometheus_instance(self, instance):
        """
        Create a copy of the instance and set default values.
        This is so the base class can create a scraper_config with the proper values.
        """
        kube_scheduler_conn_info = get_connection_info()

        # dummy needed in case kube scheduler isn't running when the check is first
        endpoint = kube_scheduler_conn_info.get('url') if kube_scheduler_conn_info is not None else "dummy_url/cadvisor"

        sli_instance = deepcopy(instance)
        sli_instance.update(
            {
                'namespace': self.NAMESPACE,
                'prometheus_url': instance.get('sli_metrics_endpoint', self.urljoin(endpoint, SLI_METRICS_PATH)),
                'ignore_metrics': [
                    # 'container_fs_inodes_free',
                ],
                # # Defaults that were set when CadvisorPrometheusScraper was based on PrometheusScraper
                # 'send_monotonic_counter': instance.get('send_monotonic_counter', False),
                # 'health_service_check': instance.get('health_service_check', False),
            }
        )
        return sli_instance
    
    def urljoin(*args):
        """
        Joins given arguments into an url. Trailing but not leading slashes are
        stripped for each argument.
        :return: string
        """
        return '/'.join(arg.strip('/') for arg in args)

