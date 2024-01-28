# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict

from six.moves.urllib.parse import urljoin, urlparse, urlunparse

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2

from .metrics import PROMETHEUS_METRICS_MAP
from .utils import _get_server_info

ENVOY_VERSION = {'istio_build': {'type': 'metadata', 'label': 'tag', 'name': 'version'}}

LABEL_MAP = {
    'cluster_name': 'envoy_cluster',
    'envoy_cluster_name': 'envoy_cluster',
    'envoy_local_http_ratelimit_prefix': 'stat_prefix',  # local rate limit
    'envoy_connection_limit_prefix': 'stat_prefix',  # connection limit
    'envoy_http_conn_manager_prefix': 'stat_prefix',  # tracing
    'envoy_listener_address': 'address',  # listener
    'envoy_virtual_cluster': 'virtual_envoy_cluster',  # vhost
    'envoy_virtual_host': 'virtual_host_name',  # vhost
}


METRIC_WITH_LABEL_NAME = {
    r'^envoy_server_(.+\_.+)_watchdog_miss$': {
        'label_name': 'thread_name',
        'metric_type': 'monotonic_count',
        'new_name': 'server.watchdog_miss.count',
    },
    r'^envoy_server_(.+\_.+)_watchdog_mega_miss$': {
        'label_name': 'thread_name',
        'metric_type': 'monotonic_count',
        'new_name': 'server.watchdog_mega_miss.count',
    },
    r'^envoy_(.+\_.+)_watchdog_miss$': {
        'label_name': 'thread_name',
        'metric_type': 'monotonic_count',
        'new_name': 'watchdog_miss.count',
    },
    r'^envoy_(.+\_.+)_watchdog_mega_miss$': {
        'label_name': 'thread_name',
        'metric_type': 'monotonic_count',
        'new_name': 'watchdog_mega_miss.count',
    },
    r'^envoy_cluster_circuit_breakers_(\w+)_cx_open$': {
        'label_name': 'priority',
        'metric_type': 'gauge',
        'new_name': 'cluster.circuit_breakers.cx_open',
    },
    r'^envoy_cluster_circuit_breakers_(\w+)_cx_pool_open$': {
        'label_name': 'priority',
        'metric_type': 'gauge',
        'new_name': 'cluster.circuit_breakers.cx_pool_open',
    },
    r'^envoy_cluster_circuit_breakers_(\w+)_rq_open$': {
        'label_name': 'priority',
        'metric_type': 'gauge',
        'new_name': 'cluster.circuit_breakers.rq_open',
    },
    r'^envoy_cluster_circuit_breakers_(\w+)_rq_pending_open$': {
        'label_name': 'priority',
        'metric_type': 'gauge',
        'new_name': 'cluster.circuit_breakers.rq_pending_open',
    },
    r'^envoy_cluster_circuit_breakers_(\w+)_rq_retry_open$': {
        'label_name': 'priority',
        'metric_type': 'gauge',
        'new_name': 'cluster.circuit_breakers.rq_retry_open',
    },
    r'^envoy_listener_admin_(.+\_.+)_downstream_cx_active$': {
        'label_name': 'handler',
        'metric_type': 'gauge',
        'new_name': 'listener.admin.downstream_cx_active',
    },
    r'^envoy_listener_(.+\_.+)_downstream_cx_active$': {
        'label_name': 'handler',
        'metric_type': 'gauge',
        'new_name': 'listener.downstream_cx_active',
    },
    r'^envoy_listener_admin_(.+\_.+)_downstream_cx$': {
        'label_name': 'handler',
        'metric_type': 'monotonic_count',
        'new_name': 'listener.admin.downstream_cx.count',
    },
    r'^envoy_listener_(.+)_downstream_cx$': {
        'label_name': 'handler',
        'metric_type': 'monotonic_count',
        'new_name': 'listener.downstream_cx.count',
    },
    r'envoy_connection_limit_(.+)_active_connections$': {
        'label_name': 'stat_prefix',
        'metric_type': 'gauge',
        'new_name': 'connection_limit.active_connections',
    },
    r'envoy_connection_limit_(.+)_limited_connections$': {
        'label_name': 'stat_prefix',
        'metric_type': 'monotonic_count',
        'new_name': 'connection_limit.limited_connections.count',
    },
    r'envoy_(.+)_http_local_rate_limit_enabled$': {
        'label_name': 'stat_prefix',
        'metric_type': 'monotonic_count',
        'new_name': 'http.local_rate_limit_enabled.count',
    },
    r'envoy_(.+)_http_local_rate_limit_enforced$': {
        'label_name': 'stat_prefix',
        'metric_type': 'monotonic_count',
        'new_name': 'http.local_rate_limit_enforced.count',
    },
    r'envoy_(.+)_http_local_rate_limit_ok$': {
        'label_name': 'stat_prefix',
        'metric_type': 'monotonic_count',
        'new_name': 'http.local_rate_limit_ok.count',
    },
    r'envoy_(.+)_http_local_rate_limit_rate_limited$': {
        'label_name': 'stat_prefix',
        'metric_type': 'monotonic_count',
        'new_name': 'http.local_rate_limit_rate_limited.count',
    },
    r'envoy_cluster_(.+)_client_ssl_socket_factory_downstream_context_secrets_not_ready$': {
        'label_name': 'envoy_service',
        'metric_type': 'monotonic_count',
        'new_name': 'cluster.client_ssl_socket_factory.downstream_context_secrets_not_ready.count',
    },
    r'envoy_cluster_(.+)_client_ssl_socket_factory_upstream_context_secrets_not_ready$': {
        'label_name': 'envoy_service',
        'metric_type': 'monotonic_count',
        'new_name': 'cluster.client_ssl_socket_factory.upstream_context_secrets_not_ready.count',
    },
    r'envoy_cluster_(.+)_client_ssl_socket_factory_ssl_context_update_by_sds$': {
        'label_name': 'envoy_service',
        'metric_type': 'monotonic_count',
        'new_name': 'cluster.client_ssl_socket_factory.ssl_context_update_by_sds.count',
    },
    r'envoy_listener_(.+)_server_ssl_socket_factory_upstream_context_secrets_not_ready': {
        'label_name': 'envoy_address',
        'metric_type': 'monotonic_count',
        'new_name': 'listener.server_ssl_socket_factory.upstream_context_secrets_not_ready.count',
    },
    r'envoy_listener_(.+)_server_ssl_socket_factory_ssl_context_update_by_sds': {
        'label_name': 'envoy_address',
        'metric_type': 'monotonic_count',
        'new_name': 'listener.server_ssl_socket_factory.ssl_context_update_by_sds.count',
    },
    r'envoy_listener_(.+)_server_ssl_socket_factory_downstream_context_secrets_not_ready': {
        'label_name': 'envoy_address',
        'metric_type': 'monotonic_count',
        'new_name': 'listener.server_ssl_socket_factory.downstream_context_secrets_not_ready.count',
    },
}


class EnvoyCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'envoy'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.append(self.configure_additional_transformers)
        openmetrics_endpoint = self.instance.get('openmetrics_endpoint')
        self.collect_server_info = self.instance.get('collect_server_info', True)

        self.base_url = None
        try:
            parts = urlparse(openmetrics_endpoint)
            self.base_url = urlunparse(parts[:2] + ('', '', None, None))

        except Exception as e:
            self.log.debug("Unable to determine the base url for version collection: %s", str(e))

    def check(self, _):
        self._collect_metadata()
        super(EnvoyCheckV2, self).check(None)

    def get_default_config(self):
        return {
            'metrics': [PROMETHEUS_METRICS_MAP],
            'rename_labels': LABEL_MAP,
        }

    def configure_transformer_label_in_name(self, metric_pattern, new_name, label_name, metric_type):
        method = getattr(self, metric_type)
        cached_patterns = defaultdict(lambda: re.compile(metric_pattern))

        def transform(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                parsed_sample_name = sample.name
                if sample.name.endswith("_total"):
                    parsed_sample_name = re.match("(.*)_total$", sample.name).groups()[0]
                label_value = cached_patterns[metric_pattern].match(parsed_sample_name).groups()[0]

                tags.append('{}:{}'.format(label_name, label_value))
                method(new_name, sample.value, tags=tags, hostname=hostname)

        return transform

    def configure_additional_transformers(self):
        for metric, data in METRIC_WITH_LABEL_NAME.items():
            self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
                metric, self.configure_transformer_label_in_name(metric, **data), pattern=True
            )

    @AgentCheck.metadata_entrypoint
    def _collect_metadata(self):
        # Replace in favor of built-in Openmetrics metadata when PR is available
        # https://github.com/envoyproxy/envoy/pull/18991
        if not self.base_url:
            self.log.debug("Skipping server info collection due to malformed url: %s", self.base_url)
            return

        # From http://domain/thing/stats to http://domain/thing/server_info
        if not self.collect_server_info:
            self.log.debug("Skipping server info collection as it is disabled, collect_server_info")
            return

        server_info_url = urljoin(self.base_url, 'server_info')
        raw_version = _get_server_info(server_info_url, self.log, self.http)

        if raw_version:
            self.set_metadata('version', raw_version)
