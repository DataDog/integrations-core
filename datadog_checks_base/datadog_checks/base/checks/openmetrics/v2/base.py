# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import ChainMap
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from requests.exceptions import RequestException

from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.tracing import traced_class

from .metrics_file import MetricsConfig, MetricsFile
from .scraper import OpenMetricsScraper

if TYPE_CHECKING:
    from collections.abc import Mapping


class OpenMetricsBaseCheckV2(AgentCheck):
    """
    OpenMetricsBaseCheckV2 is an updated class of OpenMetricsBaseCheck to scrape endpoints that emit Prometheus metrics.

    Minimal example configuration:

    ```yaml
    instances:
    - openmetrics_endpoint: http://example.com/endpoint
      namespace: "foobar"
      metrics:
      - bar
      - foo
    ```

    """

    DEFAULT_METRIC_LIMIT = 2000

    METRICS_FILES: list[MetricsFile] = []
    """Declare YAML files containing metric name mappings to load automatically.

    When set, each file is loaded and its metrics are appended to the default
    config's ``metrics`` list. Files with a predicate are only loaded when the
    predicate evaluates to ``True`` against the instance configuration.

    When empty (the default), the base check looks for a ``metrics.yml`` file
    next to the check module and loads it automatically if found.

    Example::

        from pathlib import Path
        from datadog_checks.base.checks.openmetrics.v2.metrics_file import (
            ConfigOptionTruthy,
            MetricsFile,
        )

        class MyCheck(OpenMetricsBaseCheckV2):
            METRICS_FILES = [
                MetricsFile(Path("metrics/default.yaml")),
                MetricsFile(Path("metrics/go.yaml"), predicate=ConfigOptionTruthy("go_metrics")),
            ]
    """

    # Allow tracing for openmetrics integrations
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        return traced_class(cls)

    def __init__(self, name, init_config, instances):
        """
        The base class for any OpenMetrics-based integration.

        Subclasses are expected to override this to add their custom scrapers or transformers.
        When overriding, make sure to call this (the parent's) __init__ first!
        """
        super(OpenMetricsBaseCheckV2, self).__init__(name, init_config, instances)

        # All desired scraper configurations, which subclasses can override as needed
        self.scraper_configs = [self.instance]

        # All configured scrapers keyed by the endpoint
        self.scrapers = {}

        self.check_initializations.append(self.configure_scrapers)

    def check(self, _):
        """
        Perform an openmetrics-based check.

        Subclasses should typically not need to override this, as most common customization
        needs are covered by the use of custom scrapers.
        Another thing to note is that this check ignores its instance argument completely.
        We take care of instance-level customization at initialization time.
        """
        self.refresh_scrapers()

        for endpoint, scraper in self.scrapers.items():
            self.log.debug('Scraping OpenMetrics endpoint: %s', endpoint)

            with self.adopt_namespace(scraper.namespace):
                try:
                    scraper.scrape()
                except (ConnectionError, RequestException) as e:
                    self.log.error("There was an error scraping endpoint %s: %s", endpoint, str(e))
                    raise type(e)("There was an error scraping endpoint {}: {}".format(endpoint, e)) from None

    def configure_scrapers(self):
        """
        Creates a scraper configuration for each instance.
        """

        scrapers = {}

        for config in self.scraper_configs:
            endpoint = config.get('openmetrics_endpoint', '')
            if not isinstance(endpoint, str):
                raise ConfigurationError('The setting `openmetrics_endpoint` must be a string')
            elif not endpoint:
                raise ConfigurationError('The setting `openmetrics_endpoint` is required')

            scrapers[endpoint] = self.create_scraper(config)

        self.scrapers.clear()
        self.scrapers.update(scrapers)

    def create_scraper(self, config):
        """
        Subclasses can override to return a custom scraper based on instance configuration.
        """
        return OpenMetricsScraper(self, self.get_config_with_defaults(config))

    def set_dynamic_tags(self, *tags):
        for scraper in self.scrapers.values():
            scraper.set_dynamic_tags(*tags)

    def get_config_with_defaults(self, config):
        defaults = self.get_default_config()
        file_metrics = self._load_file_based_metrics(config)
        if file_metrics:
            defaults.setdefault('metrics', []).extend(file_metrics)
        return ChainMap(config, defaults)

    def get_default_config(self):
        return {}

    def refresh_scrapers(self):
        pass

    def _load_file_based_metrics(self, config: Mapping) -> list[MetricsConfig]:
        """Load metric mappings from YAML files declared in ``METRICS_FILES``.

        If ``METRICS_FILES`` is empty, falls back to convention-based discovery
        by looking for a ``metrics.yml`` file in the check's package directory.
        """
        metrics_files = self.METRICS_FILES

        if not metrics_files:
            default_path = self._get_package_dir() / "metrics.yml"
            if default_path.is_file():
                metrics_files = [MetricsFile(Path("metrics.yml"))]
            else:
                return []

        metrics: list[MetricsConfig] = []
        for source in metrics_files:
            if source.predicate is None or source.predicate.should_load(config):
                data = self._load_metrics_file(source.path)
                metrics.append(data)
        return metrics

    def _load_metrics_file(self, path: Path) -> MetricsConfig:
        """Load and parse a single YAML metrics file."""
        file_path = self._get_package_dir() / path
        with open(file_path) as f:
            return yaml.safe_load(f)

    @contextmanager
    def adopt_namespace(self, namespace):
        old_namespace = self.__NAMESPACE__

        try:
            self.__NAMESPACE__ = namespace or old_namespace
            yield
        finally:
            self.__NAMESPACE__ = old_namespace
