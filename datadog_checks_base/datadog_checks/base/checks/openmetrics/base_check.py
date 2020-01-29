# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ...errors import CheckException
from .. import AgentCheck
from .mixins import OpenMetricsScraperMixin


class OpenMetricsBaseCheck(OpenMetricsScraperMixin, AgentCheck):
    """
    OpenMetricsBaseCheck is a class that helps instantiating PrometheusCheck only
    with YAML configurations. As each check has it own states it maintains a map
    of all checks so that the one corresponding to the instance is executed.
    Minimal example configuration::

        instances:
        - prometheus_url: http://example.com/endpoint
            namespace: "foobar"
            metrics:
            - bar
            - foo


    Agent 5 signature:

        OpenMetricsBaseCheck(name, init_config, agentConfig, instances=None, default_instances=None,
                             default_namespace=None)

    Agent 6 signature:

        OpenMetricsBaseCheck(name, init_config, instances, default_instances=None, default_namespace=None)

    """

    DEFAULT_METRIC_LIMIT = 2000

    HTTP_CONFIG_REMAPPER = {
        'ssl_verify': {'name': 'tls_verify'},
        'ssl_cert': {'name': 'tls_cert'},
        'ssl_private_key': {'name': 'tls_private_key'},
        'ssl_ca_cert': {'name': 'tls_ca_cert'},
        'prometheus_timeout': {'name': 'timeout'},
    }

    def __init__(self, *args, **kwargs):
        default_instances = kwargs.pop('default_instances', None) or {}
        default_namespace = kwargs.pop('default_namespace', None)

        super(OpenMetricsBaseCheck, self).__init__(*args, **kwargs)

        self.default_instances = default_instances
        self.default_namespace = default_namespace
        self.config_map = {}
        self._http_handlers = {}

        # pre-generate the scraper configurations
        # NOTE: this is a HACK. We should be accepting a dedicated parameter for populating `.config_map`, such as
        # a 'configuration_instances' parameter. In practice, the Agent will NOT be passing multiple instances,
        # so we must make sure not to break that contract by allowing subclasses to pass multiple instances.

        for instance in self.instances:
            self.get_scraper_config(instance)

    def check(self, instance):
        # Get the configuration for this specific instance
        scraper_config = self.get_scraper_config(instance)

        # We should be specifying metrics for checks that are vanilla OpenMetricsBaseCheck-based
        if not scraper_config['metrics_mapper']:
            raise CheckException(
                "You have to collect at least one metric from the endpoint: {}".format(scraper_config['prometheus_url'])
            )

        self.process(scraper_config)

    def get_scraper_config(self, instance, override_existing=False):
        # NOTE: 'override_existing=True' is meant for testing purposes only.
        endpoint = instance.get('prometheus_url')

        if endpoint is None:
            raise CheckException("Unable to find prometheus URL in config file.")

        # If we've already created the corresponding scraper configuration, return it
        if endpoint in self.config_map and not override_existing:
            return self.config_map[endpoint]

        # Otherwise, we create the scraper configuration
        config = self.create_scraper_configuration(instance)

        # Add this configuration to the config_map
        self.config_map[endpoint] = config

        return config

    def _finalize_tags_to_submit(self, _tags, metric_name, val, metric, custom_tags=None, hostname=None):
        """
        Format the finalized tags
        This is generally a noop, but it can be used to change the tags before sending metrics
        """
        return _tags

    def _filter_metric(self, metric, scraper_config):
        """
        Used to filter metrics at the begining of the processing, by default no metric is filtered
        """
        return False
