# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap
from contextlib import contextmanager

from requests.exceptions import RequestException

from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.errors import ConfigurationError
from datadog_checks.base.utils.tracing import traced_class

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

    # Subclasses can override to specify well-known port(s) for discovery.
    DISCOVERY_PORT_HINTS: list[int] = []

    # Subclasses can override if metrics are not at /metrics.
    DISCOVERY_METRICS_PATH: str = "/metrics"

    # Allow tracing for openmetrics integrations
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        return traced_class(cls)

    # Placeholder endpoint injected into trial-mode instances so the parent's
    # configuration-model validation and configure_scrapers don't fail before
    # _resolve_discovery has picked the real endpoint.
    _DISCOVERY_PLACEHOLDER_ENDPOINT = "http://discovery-pending.invalid/metrics"

    def __init__(self, name, init_config, instances):
        """
        The base class for any OpenMetrics-based integration.

        Subclasses are expected to override this to add their custom scrapers or transformers.
        When overriding, make sure to call this (the parent's) __init__ first!
        """
        if instances:
            for inst in instances:
                if inst.get("__discovery_service__") is not None and not inst.get("openmetrics_endpoint"):
                    inst["openmetrics_endpoint"] = self._DISCOVERY_PLACEHOLDER_ENDPOINT

        super(OpenMetricsBaseCheckV2, self).__init__(name, init_config, instances)

        # All desired scraper configurations, which subclasses can override as needed
        self.scraper_configs = [self.instance]

        # All configured scrapers keyed by the endpoint
        self.scrapers = {}

        # True once a trial-mode (config-discovery) instance has resolved its
        # endpoint and the scrapers have been (re)configured.
        self._discovery_resolved = False

        self.check_initializations.append(self.configure_scrapers)

    def check(self, _):
        """
        Perform an openmetrics-based check.

        Subclasses should typically not need to override this, as most common customization
        needs are covered by the use of custom scrapers.
        Another thing to note is that this check ignores its instance argument completely.
        We take care of instance-level customization at initialization time.
        """
        if self.instance.get("__discovery_service__") is not None and not self._discovery_resolved:
            self._resolve_discovery(self.instance["__discovery_service__"])

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
            # Trial-mode instance: the placeholder endpoint is set so config-model
            # validation passes, but we don't want a real scraper for it. Skip
            # until _resolve_discovery sets the real endpoint and re-invokes us.
            if config.get("__discovery_service__") is not None and not self._discovery_resolved:
                continue
            endpoint = config.get('openmetrics_endpoint', '')
            if not isinstance(endpoint, str):
                raise ConfigurationError('The setting `openmetrics_endpoint` must be a string')
            elif not endpoint:
                raise ConfigurationError('The setting `openmetrics_endpoint` is required')

            scrapers[endpoint] = self.create_scraper(config)

        self.scrapers.clear()
        self.scrapers.update(scrapers)

    def _resolve_discovery(self, service_dict):
        """Probe candidate ports and configure scrapers for the responding endpoint.

        Called from check() on the first run for trial-mode instances. Subclasses
        can override to customize behavior after the endpoint is resolved (e.g. to
        derive related fields from openmetrics_endpoint). The override must call
        super()._resolve_discovery first.
        """
        # Module-attribute access for http_probe so tests can monkeypatch it.
        import datadog_checks.base.utils.discovery.http as http_mod
        from datadog_checks.base.utils.discovery import (
            Port,
            Service,
            candidate_ports,
            is_prometheus_exposition,
        )

        service = Service(
            id=service_dict["id"],
            host=service_dict["host"],
            ports=tuple(Port(number=p["number"], name=p.get("name", "")) for p in service_dict["ports"]),
        )

        endpoint = None
        for port in candidate_ports(service, self.DISCOVERY_PORT_HINTS):
            if http_mod.http_probe(
                service.host,
                port.number,
                self.DISCOVERY_METRICS_PATH,
                verifier=is_prometheus_exposition(),
            ):
                endpoint = f"http://{service.host}:{port.number}{self.DISCOVERY_METRICS_PATH}"
                break

        if endpoint is None:
            tried = [p.number for p in candidate_ports(service, self.DISCOVERY_PORT_HINTS)]
            raise ConfigurationError(
                f"openmetrics discovery: no responding {self.DISCOVERY_METRICS_PATH} "
                f"endpoint on {service.host} (ports tried: {tried})"
            )

        self.instance["openmetrics_endpoint"] = endpoint
        self.scraper_configs = [self.instance]
        self._discovery_resolved = True
        self.configure_scrapers()

    def create_scraper(self, config):
        """
        Subclasses can override to return a custom scraper based on instance configuration.
        """
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
