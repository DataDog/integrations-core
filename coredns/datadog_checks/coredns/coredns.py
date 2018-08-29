# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.errors import CheckException


class CoreDNSCheck(OpenMetricsBaseCheck):
    """
    Collect CoreDNS metrics from its Prometheus endpoint
    """

    # Set up metric_transformers
    METRIC_TRANSFORMERS = {}

    def __init__(self, name, init_config, agentConfig, instances=None):
        # Set up metric_transformers
        self.METRIC_TRANSFORMERS = {
            # Primarily, metrics are emitted by the prometheus plugin: https://coredns.io/plugins/metrics/
            # Note: the count metrics were moved to specific functions
            # below to be submitted as both gauges and monotonic_counts
            'coredns_dns_response_rcode_count_total': self.coredns_dns_response_rcode_count_total,
            'coredns_proxy_request_count_total': self.coredns_proxy_request_count_total,
            'coredns_cache_hits_total': self.coredns_cache_hits_total,
            'coredns_cache_misses_total': self.coredns_cache_misses_total,
            'coredns_dns_request_count_total': self.coredns_dns_request_count_total,
            'coredns_dns_request_type_count_total': self.coredns_dns_request_type_count_total,
        }

        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        super(CoreDNSCheck, self).__init__(name, init_config, agentConfig, instances=generic_instances)

    def check(self, instance):
        endpoint = instance.get('prometheus_endpoint')
        scraper_config = self.config_map[endpoint]
        self.process(scraper_config, metric_transformers=self.METRIC_TRANSFORMERS)

    def create_generic_instances(self, instances):
        """
        Transform each CoreDNS instance into a OpenMetricsBaseCheck instance
        """
        generic_instances = []
        for instance in instances:
            transformed_instance = self._create_core_dns_instance(instance)
            generic_instances.append(transformed_instance)

        return generic_instances

    def _create_core_dns_instance(self, instance):
        """
        Set up coredns instance so it can be used in OpenMetricsBaseCheck
        """
        endpoint = instance.get('prometheus_endpoint')
        if endpoint is None:
            raise CheckException("Unable to find prometheus endpoint in config file.")
        # # coredns uses 'prometheus_endpoint' and not 'prometheus_url', so we have to rename the key
        # instance['prometheus_url'] = instance.get('prometheus_endpoint', None)

        instance.update({
            'namespace': 'coredns',
            'prometheus_url': endpoint,
            'metrics': [{
                # https://coredns.io/plugins/metrics/
                'coredns_dns_request_duration_seconds': 'request_duration.seconds',
                'coredns_dns_request_size_bytes': 'request_size.bytes',
                # https://coredns.io/plugins/proxy/
                'coredns_proxy_request_duration_seconds': 'proxy_request_duration.seconds',
                # https://coredns.io/plugins/cache/
                'coredns_cache_size': 'cache_size.count',
            }]
        })

        return instance

    def submit_as_gauge_and_monotonic_count(self, metric_suffix, message, scraper_config):
        """
        submit a coredns metric both as a gauge (for compatibility) and as a monotonic_count
        """
        metric_name = scraper_config['NAMESPACE'] + metric_suffix
        for metric in message.metric:
            _tags = []
            for label in metric.label:
                _tags.append('{}:{}'.format(label.name, label.value))
            # submit raw metric
            self.gauge(metric_name, metric.counter.value, _tags)
            # submit rate metric
            self.monotonic_count(metric_name + '.count', metric.counter.value, _tags)

    def coredns_dns_response_rcode_count_total(self, message, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.response_code_count', message, scraper_config)

    def coredns_proxy_request_count_total(self, message, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.proxy_request_count', message, scraper_config)

    def coredns_cache_hits_total(self, message, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.cache_hits_count', message, scraper_config)

    def coredns_cache_misses_total(self, message, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.cache_misses_count', message, scraper_config)

    def coredns_dns_request_count_total(self, message, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.request_count', message, scraper_config)

    def coredns_dns_request_type_count_total(self, message, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.request_type_count', message, scraper_config)
