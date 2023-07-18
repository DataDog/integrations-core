# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import defaultdict

from six import PY2

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.base.constants import ServiceCheck

from .config_models import ConfigMixin
from .metrics import (
    API_SERVER_METRICS,
    APPLICATION_CONTROLLER_METRICS,
    APPSET_CONTROLLER_METRICS,
    NOTIFICATIONS_CONTROLLER_METRICS,
    REPO_SERVER_METRICS,
)

(
    API_SERVER_NAMESPACE,
    APP_CONTROLLER_NAMESPACE,
    APPSET_CONTROLLER_NAMESPACE,
    REPO_SERVER_NAMESPACE,
    NOTIFICATIONS_CONTROLLER_NAMESPACE,
) = [
    'argocd.api_server',
    'argocd.app_controller',
    'argocd.appset_controller',
    'argocd.repo_server',
    'argocd.notifications_controller',
]


class ArgocdCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        if PY2:
            raise ConfigurationError(
                "This version of the integration is only available when using py3. "
                "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                "for more information."
            )
        super(ArgocdCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self.parse_config)
        self.check_initializations.append(self.configure_additional_transformers)

    def parse_config(self):
        self.scraper_configs = []
        app_controller_endpoint = self.instance.get("app_controller_endpoint")
        appset_controller_endpoint = self.instance.get("appset_controller_endpoint")
        api_server_endpoint = self.instance.get("api_server_endpoint")
        repo_server_endpoint = self.instance.get("repo_server_endpoint")
        notifications_controller_endpoint = self.instance.get("notifications_controller_endpoint")

        if (
            not app_controller_endpoint
            and not appset_controller_endpoint
            and not repo_server_endpoint
            and not api_server_endpoint
            and not notifications_controller_endpoint
        ):
            raise ConfigurationError(
                "Must specify at least one of the following:"
                "`app_controller_endpoint`, `appset_controller_endpoint`, `repo_server_endpoint`, `api_server_endpoint`"
                " or `notifications_controller_endpoint`."
            )

        if app_controller_endpoint:
            self.scraper_configs.append(
                self.generate_config(app_controller_endpoint, APP_CONTROLLER_NAMESPACE, APPLICATION_CONTROLLER_METRICS)
            )
        if appset_controller_endpoint:
            self.scraper_configs.append(
                self.generate_config(appset_controller_endpoint, APPSET_CONTROLLER_NAMESPACE, APPSET_CONTROLLER_METRICS)
            )
        if api_server_endpoint:
            self.scraper_configs.append(
                self.generate_config(api_server_endpoint, API_SERVER_NAMESPACE, API_SERVER_METRICS)
            )
        if repo_server_endpoint:
            self.scraper_configs.append(
                self.generate_config(repo_server_endpoint, REPO_SERVER_NAMESPACE, REPO_SERVER_METRICS)
            )
        if notifications_controller_endpoint:
            self.scraper_configs.append(
                self.generate_config(
                    notifications_controller_endpoint,
                    NOTIFICATIONS_CONTROLLER_NAMESPACE,
                    NOTIFICATIONS_CONTROLLER_METRICS,
                )
            )

    def generate_config(self, endpoint, namespace, metrics):
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': metrics,
            'namespace': namespace,
        }
        config.update(self.instance)
        return config

    def configure_transformer_go_memstats_alloc_bytes(self, metric_name):
        # Custom transformer to ensure we only pick up the gauge version of this metric
        # Argo CD exposes a similar metric `go_memstats_alloc_bytes_total` as a counter
        # which would also be collected under the same name and could cause inaccuracies
        # in the metric value
        def go_memstats_alloc_bytes_transformer(_metric, sample_data, _runtime_data):
            for sample, tags, hostname in sample_data:
                self.gauge(metric_name, sample.value, tags=tags, hostname=hostname)

        return go_memstats_alloc_bytes_transformer

    def configure_transformer_argocd_cluster_connection_status(self, metric_name):
        # The metric reports a 1 if connected, and 0 if not. The mapping used here:
        # OK if connected || OK if metric value is `1`
        # Critical if not connected || Critical if value is '0'
        # Unknown for everything else
        status_map = defaultdict(lambda: ServiceCheck.UNKNOWN)
        status_map[0], status_map[1] = ServiceCheck.CRITICAL, ServiceCheck.OK
        service_check_method = self.service_check

        def argocd_cluster_connection_status_transformer(_metric, sample_data, _runtime_data):
            for sample, tags, hostname in sample_data:
                service_check_method(metric_name, status_map[int(sample.value)], hostname=hostname, tags=tags)

        return argocd_cluster_connection_status_transformer

    def configure_additional_transformers(self):
        endpoints = [key for key in self.instance.keys() if "_endpoint" in key]
        for endpoint in endpoints:
            if endpoint == "app_controller_endpoint":
                self.scrapers[self.instance[endpoint]].metric_transformer.add_custom_transformer(
                    "argocd_cluster_connection_status",
                    self.configure_transformer_argocd_cluster_connection_status("cluster.connection.status"),
                )
            self.scrapers[self.instance[endpoint]].metric_transformer.add_custom_transformer(
                "go_memstats_alloc_bytes",
                self.configure_transformer_go_memstats_alloc_bytes("go.memstats.alloc_bytes"),
            )
