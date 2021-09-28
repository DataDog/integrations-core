# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import requests
from six import PY2

from ...errors import CheckException
from .. import AgentCheck
from .mixins import OpenMetricsScraperMixin

STANDARD_FIELDS = [
    'prometheus_url',
    'namespace',
    'metrics',
    'prometheus_metrics_prefix',
    'health_service_check',
    'label_to_hostname',
    'label_joins',
    'labels_mapper',
    'type_overrides',
    'send_histograms_buckets',
    'send_distribution_buckets',
    'send_monotonic_counter',
    'send_monotonic_with_gauge',
    'send_distribution_counts_as_monotonic',
    'send_distribution_sums_as_monotonic',
    'exclude_labels',
    'bearer_token_auth',
    'bearer_token_path',
    'ignore_metrics',
]


class OpenMetricsBaseCheck(OpenMetricsScraperMixin, AgentCheck):
    """
    OpenMetricsBaseCheck is a class that helps scrape endpoints that emit Prometheus metrics only
    with YAML configurations.

    Minimal example configuration:

        instances:
        - prometheus_url: http://example.com/endpoint
            namespace: "foobar"
            metrics:
            - bar
            - foo

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
        'request_size': {'name': 'request_size', 'default': 10},
    }

    def __init__(self, *args, **kwargs):
        """
        The base class for any Prometheus-based integration.
        """
        args = list(args)
        default_instances = kwargs.pop('default_instances', None) or {}
        default_namespace = kwargs.pop('default_namespace', None)

        legacy_kwargs_in_args = args[4:]
        del args[4:]

        if len(legacy_kwargs_in_args) > 0:
            default_instances = legacy_kwargs_in_args[0] or {}
        if len(legacy_kwargs_in_args) > 1:
            default_namespace = legacy_kwargs_in_args[1]

        super(OpenMetricsBaseCheck, self).__init__(*args, **kwargs)
        self.config_map = {}
        self._http_handlers = {}
        self.default_instances = default_instances
        self.default_namespace = default_namespace

        # pre-generate the scraper configurations

        if 'instances' in kwargs:
            instances = kwargs['instances']
        elif len(args) == 4:
            # instances from agent 5 signature
            instances = args[3]
        elif isinstance(args[2], (tuple, list)):
            # instances from agent 6 signature
            instances = args[2]
        else:
            instances = None

        if instances is not None:
            for instance in instances:
                possible_urls = instance.get('possible_prometheus_urls')
                if possible_urls is not None:
                    for url in possible_urls:
                        try:
                            new_instance = deepcopy(instance)
                            new_instance.update({'prometheus_url': url})
                            scraper_config = self.get_scraper_config(new_instance)
                            response = self.send_request(url, scraper_config)
                            response.raise_for_status()
                            instance['prometheus_url'] = url
                            self.get_scraper_config(instance)
                            break
                        except (IOError, requests.HTTPError, requests.exceptions.SSLError) as e:
                            self.log.info("Couldn't connect to %s: %s, trying next possible URL.", url, str(e))
                    else:
                        self.log.error(
                            "The agent could connect to none of the following URL: %s.",
                            possible_urls,
                        )
                else:
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

    def get_scraper_config(self, instance):
        """
        Validates the instance configuration and creates a scraper configuration for a new instance.
        If the endpoint already has a corresponding configuration, return the cached configuration.
        """
        endpoint = instance.get('prometheus_url')

        if endpoint is None:
            raise CheckException("Unable to find prometheus URL in config file.")

        # If we've already created the corresponding scraper configuration, return it
        if endpoint in self.config_map:
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
        Used to filter metrics at the beginning of the processing, by default no metric is filtered
        """
        return False


# For documentation generation
# TODO: use an enum and remove STANDARD_FIELDS when mkdocstrings supports it
class StandardFields(object):
    pass


if not PY2:
    StandardFields.__doc__ = '\n'.join('- `{}`'.format(field) for field in STANDARD_FIELDS)
