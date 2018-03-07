# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib

# 3rd party
import requests

# project
try:
    # Agent5 compatibility layer
    from datadog_checks.errors import CheckException
    from datadog_checks.checks.prometheus import PrometheusCheck
except ImportError:
    from checks import CheckException
    from checks.prometheus_check import PrometheusCheck
from .metrics import DEFAULT_METRICS, DEFAULT_METRICS_TYPES

EVENT_TYPE = SOURCE_TYPE_NAME = 'linkerd'

PROMETHEUS_ENDPOINT = '/admin/metrics/prometheus'
PING_ENDPOINT = '/admin/ping'

SERVICE_CHECK_NAME = 'linkerd.can_connect'

class LinkerdCheck(PrometheusCheck):
    """
    Collect linkerd metrics from Prometheus
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(LinkerdCheck, self).__init__(name, init_config, agentConfig, instances)
        self.NAMESPACE = 'linkerd'

        self.metrics_mapper = {}
        self.type_overrides = {}

        # Linkerd allows you to add a prefix for the metrics in the configuration
        prefix = self.init_config.get("linkerd_prometheus_prefix", '')
        for m in DEFAULT_METRICS:
            self.metrics_mapper[prefix + m] = DEFAULT_METRICS[m]
        for m in DEFAULT_METRICS_TYPES:
            self.type_overrides[prefix + m] = DEFAULT_METRICS_TYPES[m]


    def _finalize_tags_to_submit(self, _tags, metric_name, val, metric, custom_tags=None, hostname=None):
        return _tags

    def check(self, instance):
        admin_ip = instance.get('admin_ip')
        admin_port = instance.get('admin_port')
        prometheus_endpoint = instance.get('prometheus_endpoint') or PROMETHEUS_ENDPOINT

        if admin_ip is None or admin_port is None:
            raise CheckException("Unable to find admin_ip and admin_port in config file.")


        prometheus_url = "http://{}:{}{}".format(
            admin_ip,
            admin_port,
            prometheus_endpoint
        )

        ping_url = "http://{}:{}{}".format(
            admin_ip,
            admin_port,
            PING_ENDPOINT
        )

        tags = ["linkerd_admin_ip:{}".format(admin_ip), "linkerd_admin_port:{}".format(admin_port)]

        try:
            r = requests.get(ping_url)
            r.raise_for_status()
            if r.content == "pong":
                self.service_check(SERVICE_CHECK_NAME, PrometheusCheck.OK,
                               tags=tags)
            else:
                self.service_check(SERVICE_CHECK_NAME, PrometheusCheck.UNKNOWN,
                               tags=tags)
                raise CheckException("Error pinging {}. Server responded with: {}".format(ping_url, r.content))
        except requests.exceptions.HTTPError as e:
            self.service_check(SERVICE_CHECK_NAME, PrometheusCheck.CRITICAL,
                               tags=tags)
            raise CheckException("Error pinging {}. Error: {}".format(ping_url, e))

        self.process(prometheus_url, send_histograms_buckets=True, instance=instance)
