# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from copy import deepcopy

from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck

SLI_METRICS_PATH = '/slis'

SLI_METRICS_MAP = {
    'kubernetes_healthcheck': 'kubernetes_healthcheck',
    'kubernetes_healthchecks_total': 'kubernetes_healthchecks_total',
}


class SliMetricsScraperMixin(OpenMetricsBaseCheck):
    """
    This class scrapes metrics for the kube controller manager "/metrics/sli" prometheus endpoint and submits them on
    behalf of a check.
    """

    def __init__(self, *args, **kwargs):
        super(SliMetricsScraperMixin, self).__init__(*args, **kwargs)
        self.sli_transformers = {
            'kubernetes_healthcheck': self.sli_metrics_transformer,
            'kubernetes_healthchecks_total': self.sli_metrics_transformer,
        }

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
            }
        )
        return sli_instance

    def detect_sli_endpoint(self, http_handler, url):
        """
        Whether the SLI metrics endpoint is available (k8s 1.26+).
        :return: true if the endpoint returns 200, false otherwise.
        """
        try:
            r = http_handler.get(url, stream=True)
        except Exception as e:
            self.log.debug("Error querying SLIs endpoint: %s", e)
            return False
        if r.status_code == 403:
            self.log.debug(
                "The /metrics/slis endpoint was introduced in Kubernetes v1.26. If you expect to see SLI metrics, \
                please check that your permissions are configured properly."
            )
        return r.status_code == 200

    def sli_metrics_transformer(self, metric, scraper_config):
        modified_metric = deepcopy(metric)
        modified_metric.samples = []

        for sample in metric.samples:
            metric_type = sample[self.SAMPLE_LABELS]["type"]
            if metric_type == "healthz":
                self._rename_sli_tag(sample, "sli_name", "name")
                self._remove_tag(sample, "type")
                modified_metric.samples.append(sample)
            else:
                self.log.debug("Skipping metric with type `%s`", metric_type)
        self.submit_openmetric(SLI_METRICS_MAP[modified_metric.name], modified_metric, scraper_config)

    def _rename_sli_tag(self, sample, new_tag_name, old_tag_name):
        sample[self.SAMPLE_LABELS][new_tag_name] = sample[self.SAMPLE_LABELS][old_tag_name]
        del sample[self.SAMPLE_LABELS][old_tag_name]

    def _remove_tag(self, sample, tag_name):
        del sample[self.SAMPLE_LABELS][tag_name]
