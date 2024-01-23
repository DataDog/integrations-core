# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

from copy import deepcopy

from datadog_checks.base.checks.kubelet_base.base import urljoin
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.utils.tagging import tagger

from .common import get_container_label, replace_container_rt_prefix, tags_for_docker

PROBES_METRICS_PATH = '/metrics/probes'


class ProbesPrometheusScraperMixin(object):
    """
    This class scrapes metrics for the kubelet "/metrics/probes" prometheus endpoint and submits
    them on behalf of a check.
    """

    def __init__(self, *args, **kwargs):
        super(ProbesPrometheusScraperMixin, self).__init__(*args, **kwargs)

        self._probes_available = None
        self.PROBES_METRIC_TRANSFORMERS = {
            'prober_probe_total': self.prober_probe_total,
        }

    def _create_probes_prometheus_instance(self, instance, prom_url):
        """
        Create a copy of the instance and set default values.
        This is so the base class can create a scraper_config with the proper values.
        """
        probes_instance = deepcopy(instance)
        probes_instance.update(
            {
                'namespace': self.NAMESPACE,
                'prometheus_url': instance.get('probes_metrics_endpoint', urljoin(prom_url, PROBES_METRICS_PATH)),
            }
        )
        return probes_instance

    def detect_probes(self, http_handler, url):
        """
        Whether the probe metrics endpoint is available (k8s 1.15+).
        :return: false if the endpoint throws a 404, true otherwise.
        """
        if self._probes_available is not None:
            return self._probes_available
        try:
            r = http_handler.head(url)
        except Exception as e:
            self.log.debug("Unable to collect query probes endpoint: %s", e)
            return False
        self._probes_available = r.status_code != 404
        return self._probes_available

    def prober_probe_total(self, metric, scraper_config):
        for sample in metric.samples:
            metric_name_suffix = ''
            labels = sample[OpenMetricsBaseCheck.SAMPLE_LABELS]

            probe_type = labels.get('probe_type')
            if probe_type == 'Liveness':
                metric_name_suffix = '.liveness_probe'
            elif probe_type == 'Readiness':
                metric_name_suffix = '.readiness_probe'
            elif probe_type == 'Startup':
                metric_name_suffix = '.startup_probe'
            else:
                self.log.debug("Unsupported probe type %s", probe_type)
                continue

            result = labels.get('result')
            if result == 'successful':
                metric_name_suffix = metric_name_suffix + '.success.total'
            elif result == 'failed':
                metric_name_suffix = metric_name_suffix + '.failure.total'
            elif result == 'unknown':
                metric_name_suffix = metric_name_suffix + '.unknown.total'
            else:
                self.log.debug("Unsupported probe result %s", result)
                continue

            metric_name = scraper_config['namespace'] + metric_name_suffix

            container_id = self.pod_list_utils.get_cid_by_labels(labels)
            if container_id is None:
                self.log.debug(
                    "Container id not found from /pods for container: %s/%s/%s - no metrics will be sent",
                    get_container_label(labels, 'namespace'),
                    get_container_label(labels, 'pod'),
                    get_container_label(labels, 'container'),
                )
                continue

            if self.pod_list_utils.is_excluded(container_id):
                continue

            container_tags = tags_for_docker(replace_container_rt_prefix(container_id), tagger.HIGH, True)
            if not container_tags:
                self.log.debug(
                    "Tags not found for container: %s/%s/%s:%s - no metrics will be sent",
                    get_container_label(labels, 'namespace'),
                    get_container_label(labels, 'pod'),
                    get_container_label(labels, 'container'),
                    container_id,
                )

            self.gauge(metric_name, sample[self.SAMPLE_VALUE], container_tags + self.instance_tags)
