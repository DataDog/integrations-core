# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap
from contextlib import contextmanager

from requests.exceptions import RequestException

from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.config import is_affirmative
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.tracing import traced_class

from .scraper import OpenMetricsScraper

# Maximum number of response body bytes captured per endpoint when collecting
# flare data.  Keeps flares from becoming excessively large for busy endpoints.
_FLARE_MAX_BODY_SIZE = 10_000


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

        Subclasses are expected to override this to add their custom scrapers or transformers.
        When overriding, make sure to call this (the parent's) __init__ first!
        """
        super(OpenMetricsBaseCheckV2, self).__init__(name, init_config, instances)

        # All desired scraper configurations, which subclasses can override as needed
        self.scraper_configs = [self.instance]

        # All configured scrapers keyed by the endpoint
        self.scrapers = {}

        self.check_initializations.append(self.configure_scrapers)

        if is_affirmative(self.instance.get('collect_endpoint_data_for_flare', False)):
            self.diagnosis.register(self._collect_endpoint_flare_data)

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

    def _collect_endpoint_flare_data(self):
        """Fetch the raw HTTP response from each configured OpenMetrics endpoint
        and record it as a diagnosis entry so it is included in Agent flares.

        Registered as a diagnosis callback when ``collect_endpoint_data_for_flare``
        is enabled in the instance configuration.  Each endpoint produces one
        entry containing the status line, response headers, and up to
        ``_FLARE_MAX_BODY_SIZE`` bytes of the response body — the equivalent of
        running ``curl -v <endpoint>``.
        """
        if not self.scrapers:
            self.diagnosis.warning(
                'endpoint_flare_data',
                'No scrapers initialised yet. Run the check at least once before generating a flare.',
                category='flare',
            )
            return

        for endpoint, scraper in self.scrapers.items():
            name = 'endpoint_flare_data[{}]'.format(endpoint)
            try:
                response = scraper.http.get(endpoint, stream=False)
                response.raise_for_status()

                status_line = 'HTTP {} {}'.format(response.status_code, response.reason)
                headers_text = '\n'.join('{}: {}'.format(k, v) for k, v in response.headers.items())
                body = response.text
                if len(body) > _FLARE_MAX_BODY_SIZE:
                    body = body[:_FLARE_MAX_BODY_SIZE] + '\n[... response truncated at {} bytes ...]'.format(
                        _FLARE_MAX_BODY_SIZE
                    )

                self.diagnosis.success(
                    name,
                    '{}\n{}\n\n{}'.format(status_line, headers_text, body),
                    category='flare',
                )
            except Exception as e:
                self.diagnosis.fail(
                    name,
                    'Failed to fetch {}: {}'.format(endpoint, e),
                    category='flare',
                )

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
