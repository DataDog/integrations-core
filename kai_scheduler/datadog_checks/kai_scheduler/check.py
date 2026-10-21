# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import NamedTuple

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper

from .config_models import ConfigMixin
from .evictions import EVICTED_PODS_METRIC, EvictedPodsTransformer
from .metrics import (
    BYTES_PER_GB,
    CONTROLLER_RUNTIME_METRICS,
    FAIR_SHARE_MEMORY_METRIC,
    FAIR_SHARE_MEMORY_NAME,
    GO_PROCESS_METRICS,
    QUEUE_CONTROLLER_METRICS,
    SCHEDULER_METRICS,
)

DEFAULT_RENAME_LABELS = {
    'queue_metadata_name': 'kai_queue',
    'queue_display_name': 'kai_queue_display_name',
    'namespace': 'kube_namespace',
    'nodepool': 'kai_nodepool',
    'OnSession': 'session_phase',
    'version': 'go_version',
}

# `queue_name` holds the display name on the scheduler but `metadata.name` on the queue-controller, so it cannot join
# their metrics; `queue_metadata_name` can.
DEFAULT_EXCLUDE_LABELS = ['queue_name']


class Component(NamedTuple):
    name: str
    endpoint_option: str
    metrics: list[dict]


COMPONENTS = (
    Component('scheduler', 'scheduler_endpoint', [SCHEDULER_METRICS, GO_PROCESS_METRICS]),
    Component(
        'queue_controller',
        'queue_controller_endpoint',
        [QUEUE_CONTROLLER_METRICS, CONTROLLER_RUNTIME_METRICS, GO_PROCESS_METRICS],
    ),
    Component('binder', 'binder_endpoint', [CONTROLLER_RUNTIME_METRICS, GO_PROCESS_METRICS]),
)


class KaiSchedulerCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'kai'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self.parse_config)
        self.check_initializations.append(self.configure_scheduler_transformers)

    def get_default_config(self):
        return {'rename_labels': dict(DEFAULT_RENAME_LABELS)}

    def parse_config(self):
        self.scraper_configs = [
            self.generate_config(component, endpoint)
            for component in COMPONENTS
            if (endpoint := self.instance.get(component.endpoint_option))
        ]
        if not self.scraper_configs:
            options = '`, `'.join(component.endpoint_option for component in COMPONENTS)
            raise ConfigurationError(f'Must specify at least one of the following: `{options}`')

    def generate_config(self, component: Component, endpoint: str) -> dict:
        return {
            **self.instance,
            'openmetrics_endpoint': endpoint,
            'metrics': component.metrics,
            'tags': [*(self.instance.get('tags') or []), f'kai_component:{component.name}'],
            'exclude_labels': [*DEFAULT_EXCLUDE_LABELS, *(self.instance.get('exclude_labels') or [])],
        }

    def create_scraper(self, config):
        return KaiOpenMetricsScraper(self, self.get_config_with_defaults(config))

    def configure_scheduler_transformers(self):
        endpoint = self.instance.get('scheduler_endpoint')
        if not endpoint:
            return

        def fair_share_memory_transformer(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                self.gauge(FAIR_SHARE_MEMORY_NAME, sample.value * BYTES_PER_GB, tags=tags, hostname=hostname)

        scraper = self.scrapers[endpoint]
        scraper.metric_transformer.add_custom_transformer(FAIR_SHARE_MEMORY_METRIC, fair_share_memory_transformer)
        scraper.metric_transformer.add_custom_transformer(
            EVICTED_PODS_METRIC, EvictedPodsTransformer(self, scraper.rename_labels)
        )


class KaiOpenMetricsScraper(OpenMetricsScraper):
    def generate_sample_data(self, metric):
        # KAI emits empty strings for unset labels, such as `queue_display_name` on a queue without a display name.
        # Every tag without a value is dropped, including configured ones.
        for sample, tags, hostname in super().generate_sample_data(metric):
            yield sample, [tag for tag in tags if not tag.endswith(':')], hostname
