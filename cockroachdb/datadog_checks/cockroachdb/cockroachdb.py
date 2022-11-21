# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck

from .metrics import METRIC_MAP


class CockroachdbCheck(OpenMetricsBaseCheck):

    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'openmetrics_endpoint' in instance:
            if PY2:
                raise ConfigurationError(
                    'This version of the integration is only available when using Python 3. '
                    'Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3/ '
                    'for more information or use the older style config.'
                )
            # TODO: when we drop Python 2 move this import up top
            from .check import CockroachdbCheckV2

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
