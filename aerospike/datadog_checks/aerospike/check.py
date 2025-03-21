# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP, METRIC_MAP_V7

RENAMED_LABELS = {'cluster_name': 'aerospike_cluster', 'service': 'aerospike_service'}


class AerospikeCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "aerospike"
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(AerospikeCheckV2, self).__init__(name, init_config, instances)
        self.exporter_url = instances[0]["openmetrics_endpoint"]
        self.build_version = None

    def get_default_config(self):
        """
        shares details of metrics map depending on aerospike version 7 or below
        """
        metric_map_to_use = self._get_metrics_map()

        return {
            'metrics': [metric_map_to_use],
            'rename_labels': RENAMED_LABELS,
        }

    def _get_metrics_map(self):
        """
        This method identified the aerospike server version by making a http call to the exporter,
        if aersopike server version is 7.0 or above, return the new metric_map_v7 defined in metrics.py
        """

        if self.build_version is None:
            self._fetch_build_info_from_metric()
            version_parts = [int(p) for p in self.build_version.split('.')]
            if self.build_version is None or version_parts[0] >= 7:
                return METRIC_MAP_V7

        return METRIC_MAP

    def _fetch_build_info_from_metric(self):
        """
        Fetch build info from the metric aerospike_node_up from OpenMetrics endpoint
        """
        try:
            response = self.http.get(self.exporter_url)
            response.raise_for_status()  # Ensure request was successful

            self.build_version = self._extract_node_up_with_build(response.text.strip())

        except Exception:
            # if any exception or unable to reach exporter fall to back Server version 7
            self.build_version = "7.2.0.0"

    def _extract_node_up_with_build(self, metrics_text):
        """
        parse the list of metrics for aerospike_node_up metrics, and get the build label
        """
        pattern = re.compile(r'aerospike_node_up\{([^}]*build="[^"]+"[^}]*)\}\s+([\d\.]+)')

        for match in pattern.finditer(metrics_text):
            labels_text, value = match.groups()

            # Convert labels into a dictionary
            labels = dict(item.split("=") for item in labels_text.split(","))
            labels = {k.strip(): v.strip('"') for k, v in labels.items()}  # Remove quotes

            return labels["build"]
