# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .metrics import METRIC_MAP, construct_metrics_config


class ExternalDNS(OpenMetricsBaseCheckV2):
    """OpenMetricsBaseCheckV2 implementation for external-dns."""

    __NAMESPACE__ = 'external_dns'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, [self._normalize_instance(i) for i in instances])

    @staticmethod
    def _normalize_instance(instance):
        # Always include the default `host -> http_host` rename (`host` is a reserved Datadog tag).
        return {**instance, 'rename_labels': {'host': 'http_host', **instance.get('rename_labels', {})}}

    def get_default_config(self):
        return {'metrics': construct_metrics_config(METRIC_MAP)}

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))
