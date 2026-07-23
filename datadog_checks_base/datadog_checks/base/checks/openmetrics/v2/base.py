# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import ChainMap
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.http_exceptions import HTTPRequestError, HTTPStatusError
from datadog_checks.base.utils.tracing import traced_class

from .scraper import OpenMetricsScraper

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .metrics_mapping import MetricsMapping, _RawMetricsConfig


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

    METRICS_MAP: tuple[MetricsMapping, ...] = ()
    """YAML files with metric name mappings to load automatically.

    When empty (default), looks for ``metrics.yaml`` next to the check module,
    falling back to ``metrics.yml`` if the former is absent. When set, only the
    declared files are loaded (with predicates controlling conditional loading).
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

        # Cache for file-based metrics loaded from METRICS_MAP; None means not yet loaded
        self._file_metrics: list[_RawMetricsConfig] | None = None

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
                except (ConnectionError, HTTPRequestError, HTTPStatusError) as e:
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
        """Combine instance config with class defaults and file-based metric mappings.

        Subclasses that override this method must call ``super().get_config_with_defaults(config)``;
        otherwise the YAML mappings declared via ``METRICS_MAP`` (or discovered by convention) are
        silently skipped.
        """
        defaults = dict(self.get_default_config())
        if file_metrics := self._load_file_based_metrics(config):
            defaults['metrics'] = list(defaults.get('metrics', [])) + file_metrics
        return ChainMap(config, defaults)

    def get_default_config(self) -> dict:
        """Return instance-level default scraper configuration values.

        The returned dict can be mutated by the framework before being wrapped
        in a ``ChainMap``. Avoid returning a shared or instance-level object to avoid
        state leakage between check executions.
        """
        return {}

    def refresh_scrapers(self):
        pass

    def _load_file_based_metrics(self, config: Mapping) -> list[_RawMetricsConfig]:
        """Load metric mappings from YAML files declared in ``METRICS_MAP``.

        Results are cached for the lifetime of the check instance. Predicates
        are evaluated once against the first ``config`` supplied; ``METRICS_MAP``
        is a class-level declaration and the instance config does not change
        between runs, so subsequent calls always receive the same effective
        configuration.

        Falls back to convention-based discovery of ``metrics.yaml`` or
        ``metrics.yml`` (in that order) when ``METRICS_MAP`` is empty.

        Permanent load failures (malformed YAML, unreadable files) are raised
        once on the first call; the cache is sealed beforehand so subsequent
        scrapes do not retry and re-raise the same error. A failure on any
        single file in a multi-file ``METRICS_MAP`` discards results from
        files loaded earlier in the same call: the cache lands as ``[]``, not
        as a partial mapping.
        """
        if self._file_metrics is not None:
            return self._file_metrics

        self._file_metrics = []
        package_dir = self._get_package_dir()
        if not self.METRICS_MAP:
            for candidate in (Path("metrics.yaml"), Path("metrics.yml")):
                resolved = package_dir / candidate
                if resolved.is_file():
                    self._file_metrics = [self._load_metrics_file(resolved)]
                    break
        else:
            self._file_metrics = [
                self._load_metrics_file(package_dir / source.path)
                for source in self.METRICS_MAP
                if source.should_load(config)
            ]

        return self._file_metrics

    def _load_metrics_file(self, file_path: Path) -> _RawMetricsConfig:
        try:
            with open(file_path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse metrics file {file_path}: {e}") from e
        except OSError as e:
            raise ConfigurationError(f"Failed to read metrics file {file_path}: {e}") from e
        if not isinstance(data, dict):
            raise ConfigurationError(f"Metrics file {file_path} must contain a YAML mapping, got {type(data).__name__}")
        return data

    @contextmanager
    def adopt_namespace(self, namespace):
        old_namespace = self.__NAMESPACE__

        try:
            self.__NAMESPACE__ = namespace or old_namespace
            yield
        finally:
            self.__NAMESPACE__ = old_namespace
