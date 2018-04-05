try:
    # Agent5 compatibility layer
    from datadog_checks.errors import CheckException
    from datadog_checks.checks.prometheus import PrometheusCheck
except ImportError:
    from checks import CheckException
    from checks.prometheus_check import PrometheusCheck

EVENT_TYPE = SOURCE_TYPE_NAME = 'kubedns'

class KubeDNSCheck(PrometheusCheck):
    """
    Collect kube-dns metrics from Prometheus
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(KubeDNSCheck, self).__init__(name, init_config, agentConfig, instances)
        self.NAMESPACE = 'kubedns'

        self.metrics_mapper = {
            # metrics have been renamed to kubedns in kubernetes 1.6.0
            'kubedns_kubedns_dns_response_size_bytes': 'response_size.bytes',
            'kubedns_kubedns_dns_request_duration_seconds': 'request_duration.seconds',
            # metrics names for kubernetes < 1.6.0
            'skydns_skydns_dns_response_size_bytes': 'response_size.bytes',
            'skydns_skydns_dns_request_duration_seconds': 'request_duration.seconds',
            # Note: the count metrics were moved to specific functions below to be submitted as both gauges and monotonic_counts
        }


    def check(self, instance):
        endpoint = instance.get('prometheus_endpoint')
        if endpoint is None:
            raise CheckException("Unable to find prometheus_endpoint in config file.")

        send_buckets = instance.get('send_histograms_buckets', True)
        # By default we send the buckets.
        if send_buckets is not None and str(send_buckets).lower() == 'false':
            send_buckets = False
        else:
            send_buckets = True

        self.process(endpoint, send_histograms_buckets=send_buckets, instance=instance)

    def submit_as_gauge_and_monotonic_count(self, metric_suffix, message, **kwargs):
    """
    submit a kube_dns metric both as a gauge (for compatibility) and as amonotonic_count
    """
        metric_name = self.NAMESPACE + metric_suffix
        for metric in message.metric:
            tags = []
            # submit raw metric
            self.gauge(metric_name, metric.counter.value, tags)
            # submit rate metric
            self.monotonic_count(metric_name + '.count', metric.counter.value, tags)

    # metrics names for kubernetes >= 1.6.0
    def kubedns_kubedns_dns_request_count_total(self, message, **kwargs):
        submit_as_gauge_and_monotonic_count('.request_count', message, **kwargs)

    def kubedns_kubedns_dns_error_count_total:
        submit_as_gauge_and_monotonic_count('.error_count', message, **kwargs)

    def kubedns_kubedns_dns_cachemiss_count_total:
        submit_as_gauge_and_monotonic_count('.cachemiss_count', message, **kwargs)

    # metrics names for kubernetes < 1.6.0
    def skydns_skydns_dns_request_count_total(self, message, **kwargs):
        self.kubedns_kubedns_dns_request_count_total(message, **kwargs)

    def skydns_skydns_dns_error_count_total(self, message, **kwargs):
        self.kubedns_kubedns_dns_error_count_total(message, **kwargs)

    def skydns_skydns_dns_cachemiss_count_total(self, message, **kwargs):
        self.kubedns_kubedns_dns_cachemiss_count_total(message, **kwargs)
