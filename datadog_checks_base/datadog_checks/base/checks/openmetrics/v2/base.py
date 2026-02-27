# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import ChainMap
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from requests.exceptions import RequestException

from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.tracing import traced_class

from .metrics_mapping import MetricsMapping, RawMetricsConfig
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

    METRICS_MAP: list[MetricsMapping] = []
    """YAML files with metric name mappings to load automatically.

    When empty (default), looks for a ``metrics.yml`` file next to the check
    module. When set, only the declared files are loaded (with predicates
    controlling conditional loading).
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
        self._apply_file_metrics(defaults, config)
        return ChainMap(config, defaults)

    def get_default_config(self):
        return {}

    def refresh_scrapers(self):
        pass

    def _apply_file_metrics(self, defaults: dict, config: Mapping) -> None:
        """Load file-based metrics and merge them into the given defaults dict."""
        file_metrics = self._load_file_based_metrics(config)
        if file_metrics:
            defaults.setdefault('metrics', []).extend(file_metrics)

    def _load_file_based_metrics(self, config: Mapping) -> list[RawMetricsConfig]:
        """Load metric mappings from YAML files declared in ``METRICS_MAP``.

        Falls back to convention-based discovery of ``metrics.yml`` when
        ``METRICS_MAP`` is empty.
        """
        if not self.METRICS_MAP:
            default_path = self._get_package_dir() / "metrics.yml"
            if not default_path.is_file():
                return []
            return [self._load_metrics_file(Path("metrics.yml"))]

        return [self._load_metrics_file(source.path) for source in self.METRICS_MAP if source.should_load(config)]

    def _load_metrics_file(self, path: Path) -> RawMetricsConfig:
        """Load and parse a single YAML metrics file."""
        import yaml

        file_path = self._get_package_dir() / path
        try:
            with open(file_path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise RuntimeError(f"Failed to parse metrics file {path}: {e}") from None
        if not isinstance(data, dict):
            raise RuntimeError(f"Metrics file {path} must contain a YAML mapping, got {type(data).__name__}")
        return data

    @contextmanager
    def adopt_namespace(self, namespace):
        old_namespace = self.__NAMESPACE__

        try:
            self.__NAMESPACE__ = namespace or old_namespace
            yield
        finally:
            self.__NAMESPACE__ = old_namespace
