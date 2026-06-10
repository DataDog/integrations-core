# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.transform import get_native_dynamic_transformer
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.base.utils.tagging import tagger

from .config_models import ConfigMixin
from .metrics import LOCAL_QUEUE_METRIC_MAP, METRIC_MAP, RESOURCE_METRIC_MAP

RESOURCE_METRIC_PATTERN = '^(' + '|'.join(re.escape(k) for k in RESOURCE_METRIC_MAP) + ')$'
LOCAL_QUEUE_METRIC_PATTERN = '^(' + '|'.join(re.escape(k) for k in LOCAL_QUEUE_METRIC_MAP) + ')$'

RESOURCE_NAME_MAP = {
    'cpu': 'cpu',
    'memory': 'memory',
    'nvidia.com/gpu': 'gpu',
}

OTHER_RESOURCE_NAME = 'other'
KUEUE_QUEUE_ENTITY_PREFIX = 'kubernetes_kueue_queue://'
KUEUE_RESOURCE_FLAVOR_ENTITY_PREFIX = 'kueue_resource_flavor://'

DEFAULT_RENAME_LABELS = {
    'cluster_queue': 'kueue_cluster_queue',
    'flavor': 'kueue_resource_flavor',
    'version': 'go_version',
}


class KueueCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'kueue'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.instance['rename_labels'] = {**DEFAULT_RENAME_LABELS, **self.instance.get('rename_labels', {})}

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}

    def create_scraper(self, config):
        return KueueOpenMetricsScraper(self, self.get_config_with_defaults(config))

    def configure_scrapers(self):
        super().configure_scrapers()

        metric_transformer = self.scrapers[self.config.openmetrics_endpoint].metric_transformer
        metric_transformer.add_custom_transformer(
            RESOURCE_METRIC_PATTERN,
            self.configure_resource_transformer(),
            pattern=True,
        )
        metric_transformer.add_custom_transformer(
            LOCAL_QUEUE_METRIC_PATTERN,
            self.configure_local_queue_transformer(),
            pattern=True,
        )

    def configure_resource_transformer(self):
        metric_transformer = self.scrapers[self.config.openmetrics_endpoint].metric_transformer
        # Built-in names are applied last so they cannot be overridden by user config.
        resource_name_map = {**(self.config.resource_name_map or {}), **RESOURCE_NAME_MAP}
        cached_transformers = {}

        def resource_transformer(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                resource = sample.labels.get('resource')
                if not resource:
                    self.log.debug('Skipping sample for %s: missing resource label', metric.name)
                    continue

                resource_name = self.normalize_resource_name(resource_name_map.get(resource, OTHER_RESOURCE_NAME))
                metric_name = f'{RESOURCE_METRIC_MAP[metric.name]}.{resource_name}'
                native_transformer = cached_transformers.get(metric_name)
                if native_transformer is None:
                    native_transformer = get_native_dynamic_transformer(
                        self, metric_name, None, metric_transformer.global_options
                    )
                    cached_transformers[metric_name] = native_transformer

                resource_tags = [tag for tag in tags if tag != f'resource:{resource}']
                resource_tags = self.rename_local_queue_tag(resource_tags)
                native_transformer(metric, [(sample, resource_tags, hostname)], runtime_data)

        return resource_transformer

    def configure_local_queue_transformer(self):
        metric_transformer = self.scrapers[self.config.openmetrics_endpoint].metric_transformer
        cached_transformers = {}

        def local_queue_transformer(metric, sample_data, runtime_data):
            metric_name = LOCAL_QUEUE_METRIC_MAP[metric.name]
            native_transformer = cached_transformers.get(metric_name)
            if native_transformer is None:
                native_transformer = get_native_dynamic_transformer(
                    self, metric_name, None, metric_transformer.global_options
                )
                cached_transformers[metric_name] = native_transformer

            new_sample_data = [
                (sample, self.rename_local_queue_tag(tags), hostname) for sample, tags, hostname in sample_data
            ]
            native_transformer(metric, new_sample_data, runtime_data)

        return local_queue_transformer

    @staticmethod
    def rename_local_queue_tag(tags: list[str]) -> list[str]:
        return [tag.replace('name:', 'kueue_local_queue:', 1) if tag.startswith('name:') else tag for tag in tags]

    @staticmethod
    def normalize_resource_name(resource_name: str) -> str:
        return resource_name.replace('/', '.').replace('-', '_')


class KueueOpenMetricsScraper(OpenMetricsScraper):
    def generate_sample_data(self, metric):
        for sample, tags, hostname in super().generate_sample_data(metric):
            tags.extend(self.get_queue_tagger_tags(metric, sample.labels))
            yield sample, tags, hostname

    @staticmethod
    def get_queue_tagger_tags(metric, labels) -> list[str]:
        tags = []

        if cluster_queue := labels.get('cluster_queue'):
            tags.extend(tagger.tag(f'{KUEUE_QUEUE_ENTITY_PREFIX}clusterqueue//{cluster_queue}', tagger.ORCHESTRATOR) or [])

        if metric.name in LOCAL_QUEUE_METRIC_MAP:
            namespace = labels.get('namespace')
            local_queue = labels.get('name')
            if namespace and local_queue:
                tags.extend(
                    tagger.tag(f'{KUEUE_QUEUE_ENTITY_PREFIX}localqueue/{namespace}/{local_queue}', tagger.ORCHESTRATOR)
                    or []
                )

        if flavor := labels.get('flavor'):
            tags.extend(tagger.tag(f'{KUEUE_RESOURCE_FLAVOR_ENTITY_PREFIX}{flavor}', tagger.ORCHESTRATOR) or [])

        return tags
