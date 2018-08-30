# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from collections import defaultdict

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.errors import CheckException
from .metrics import METRIC_MAP, TRACKED_METRICS


class CockroachdbCheck(OpenMetricsBaseCheck):
    SERVICE_CHECK_DISK_SPACE = 'cockroachdb.disk_space'

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

        tags = instance.get('tags', [])
        self.check_disk_space(tracked_metrics, instance, tags)

    def check_disk_space(self, tracked_metrics, instance, tags):
        capacity_total = tracked_metrics.get('capacity')
        capacity_available = tracked_metrics.get('capacity_available')

        if capacity_total is None or capacity_available is None:
            self.log.info(
                'Missing `capacity` and `capacity_available` metrics, skipping disk space check...'
            )
            return

        percent_remaining = capacity_available[0] / capacity_total[0] * 100

        disk_space_critical = int(instance.get('disk_space_critical', 5))
        if disk_space_critical <= percent_remaining:
            self.service_check(self.SERVICE_CHECK_DISK_SPACE, self.CRITICAL, tags=tags)
            return

        disk_space_warning = int(instance.get('disk_space_warning', 15))
        if disk_space_warning <= percent_remaining:
            self.service_check(self.SERVICE_CHECK_DISK_SPACE, self.WARNING, tags=tags)
            return

        self.service_check(self.SERVICE_CHECK_DISK_SPACE, self.OK, tags=tags)

    def track_metric(self, metric, scraper_config):
        scraper_config['_tracked_metrics'][metric.name].append(metric.samples[0][self.SAMPLE_VALUE])

        self._submit(TRACKED_METRICS[metric.name], metric, scraper_config)
