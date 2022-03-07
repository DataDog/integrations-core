# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# TODO: remove ignore when we stop invoking Mypy with --py2
# type: ignore
from collections import ChainMap
from contextlib import contextmanager

from requests.exceptions import RequestException
from six import raise_from

from ....errors import ConfigurationError
from ....utils.tracing import traced_class
from ... import AgentCheck
from .scraper import OpenMetricsScraper


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

    # Allow tracing for openmetrics integrations
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        return traced_class(cls)

    def __init__(self, name, init_config, instances):
        """
        The base class for any OpenMetrics-based integration.
        """
        super(OpenMetricsBaseCheckV2, self).__init__(name, init_config, instances)

        # All desired scraper configurations, which subclasses can override as needed
        self.scraper_configs = [self.instance]

        # All configured scrapers keyed by the endpoint
        self.scrapers = {}

        self.check_initializations.append(self.configure_scrapers)

    def check(self, _):
        self.refresh_scrapers()

        for endpoint, scraper in self.scrapers.items():
            self.log.info('Scraping OpenMetrics endpoint: %s', endpoint)

            with self.adopt_namespace(scraper.namespace):
                try:
                    scraper.scrape()
                except (ConnectionError, RequestException) as e:
                    self.log.error("There was an error scraping endpoint %s: %s", endpoint, str(e))
                    raise_from(type(e)("There was an error scraping endpoint {}: {}".format(endpoint, e)), None)

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
        # Subclasses can override to return a custom scraper based on configuration
        return OpenMetricsScraper(self, self.get_config_with_defaults(config))

    def set_dynamic_tags(self, *tags):
        for scraper in self.scrapers.values():
            scraper.set_dynamic_tags(*tags)

    def get_config_with_defaults(self, config):
        return ChainMap(config, self.get_default_config())

    def get_default_config(self):
        return {}

    def refresh_scrapers(self):
        pass

    @contextmanager
    def adopt_namespace(self, namespace):
        old_namespace = self.__NAMESPACE__

        try:
            self.__NAMESPACE__ = namespace or old_namespace
            yield
        finally:
            self.__NAMESPACE__ = old_namespace
