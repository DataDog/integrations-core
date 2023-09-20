# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from copy import deepcopy

SLI_METRICS_PATH = '/slis'

SLI_GAUGES = {
    'kubernetes_healthcheck': 'kubernetes_healthcheck',
}

SLI_COUNTERS = {
    'kubernetes_healthchecks_total': 'kubernetes_healthchecks_total',
}


class SliMetricsScraperMixin(object):
    """
    This class scrapes metrics for the kube controller manager "/metrics/sli" prometheus endpoint and submits them on
    behalf of a check.
    """

    def __init__(self, *args, **kwargs):
        super(SliMetricsScraperMixin, self).__init__(*args, **kwargs)
        self._slis_available = None

    def create_sli_prometheus_instance(self, instance):
        """
        Create a copy of the instance and set default values.
        This is so the base class can create a scraper_config with the proper values.
        """
        KUBE_CONTROLLER_MANAGER_SLI_NAMESPACE = "kube_controller_manager.slis"

        sli_instance = deepcopy(instance)
        sli_instance.update(
            {
                'namespace': KUBE_CONTROLLER_MANAGER_SLI_NAMESPACE,
                'prometheus_url': instance.get('prometheus_url') + SLI_METRICS_PATH,
                'metrics': [SLI_GAUGES, SLI_COUNTERS],
            }
        )
        return sli_instance

    def detect_sli_endpoint(self, http_handler, url):
        """
        Whether the sli metrics endpoint is available (k8s 1.26+).
        :return: false if the endpoint throws a 404 or 403, true otherwise.
        """
        if self._slis_available is not None:
            return self._slis_available
        try:
            r = http_handler.head(url)
        except Exception as e:
            self.log.debug("Error querying SLIs endpoint: %s", e)
        if r.status_code == 403:
            self.log.debug(
                "The /metrics/slis endpoint was introduced in Kubernetes v1.26. If you expect to see SLI metrics, \
                please check that your permissions are configured properly."
            )
        self._slis_available = r.status_code != 404 and r.status_code != 403
