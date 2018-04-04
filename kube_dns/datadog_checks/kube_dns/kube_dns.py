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
            # 'kubedns_kubedns_dns_request_count_total': 'request_count',
            'kubedns_kubedns_dns_error_count_total': 'error_count',
            'kubedns_kubedns_dns_cachemiss_count_total': 'cachemiss_count',
            # metrics names for kubernetes < 1.6.0
            'skydns_skydns_dns_response_size_bytes': 'response_size.bytes',
            'skydns_skydns_dns_request_duration_seconds': 'request_duration.seconds',
            # 'skydns_skydns_dns_request_count_total': 'request_count',
            'skydns_skydns_dns_error_count_total': 'error_count',
            'skydns_skydns_dns_cachemiss_count_total': 'cachemiss_count',
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

    def kubedns_kubedns_dns_request_count_total(self, message, **kwargs):
        metric_name = self.NAMESPACE + '.request_count'
        for metric in message.metric:
            tags = []
            # submit raw metric
            self.gauge(metric_name, metric.counter.value, tags)
            # submit rate metric
            self.monotonic_count(metric_name + '.count', metric.counter.value, tags)

    def skydns_skydns_dns_request_count_total(self, message, **kwargs):
        self.kubedns_kubedns_dns_request_count_total(message, **kwargs)
