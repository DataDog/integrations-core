# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck

from .check import CockroachdbCheckV2
from .metrics import METRIC_MAP


class CockroachdbCheck(OpenMetricsBaseCheck):

    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'openmetrics_endpoint' in instance:
            return CockroachdbCheckV2(name, init_config, instances)
        else:
            return super(CockroachdbCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(CockroachdbCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={
                'cockroachdb': {
                    'prometheus_url': 'http://localhost:8080/_status/vars',
                    'namespace': 'cockroachdb',
                    'metrics': [METRIC_MAP],
                    'send_histograms_buckets': True,
                    'metadata_metric_name': 'build_timestamp',
                    'metadata_label_map': {'version': 'tag'},
                }
            },
            default_namespace='cockroachdb',
        )

    def transform_metadata(self, metric, scraper_config):
        # override the method in the base class to continue to send version metric
        super(CockroachdbCheck, self).transform_metadata(metric, scraper_config)

        self.submit_openmetric('build.timestamp', metric, scraper_config)
