# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.errors import CheckException
from .metrics import METRIC_MAP, TRACKED_METRICS


class CockroachdbCheck(OpenMetricsBaseCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(CockroachdbCheck, self).__init__(
            name,
            init_config,
            agentConfig,
            instances,
            default_instances={
                'cockroachdb': {
                    'prometheus_url': 'http://localhost:8080/_status/vars',
                    'namespace': 'cockroachdb',
                    'metrics': [METRIC_MAP],
                    'send_histograms_buckets': True,
                }
            },
            default_namespace='cockroachdb',
        )

    def check(self, instance):
        scraper_config = self.get_scraper_config(instance)

        if 'prometheus_url' not in scraper_config:
            raise CheckException(
                'You have to define at least one `prometheus_url`.'
            )

        if not scraper_config.get('metrics_mapper'):
            raise CheckException(
                'You have to collect at least one metric from the endpoint `{}`.'.format(
                    scraper_config['prometheus_url']
                )
            )

        tracked_metrics = scraper_config.get('_tracked_metrics')
        if tracked_metrics is None:
            tracked_metrics = scraper_config['_tracked_metrics'] = defaultdict(list)
        else:
            tracked_metrics.clear()

        self.process(
            scraper_config,
            metric_transformers={metric: self.track_metric for metric in TRACKED_METRICS}
        )

    def track_metric(self, metric, scraper_config):
        scraper_config['_tracked_metrics'][metric.name].extend(
            sample[self.SAMPLE_VALUE] for sample in metric.samples
        )

        self._submit(TRACKED_METRICS[metric.name], metric, scraper_config)
