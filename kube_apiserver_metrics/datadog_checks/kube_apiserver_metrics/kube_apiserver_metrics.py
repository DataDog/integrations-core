# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

from six import iteritems
from datadog_checks.base import ConfigurationError
from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck


class KubeApiserverMetricsCheck(OpenMetricsBaseCheck):
    """
    Collect kubernetes apiserver metrics in the Prometheus format
    See https://github.com/kubernetes/apiserver
    """
    DEFAULT_METRIC_LIMIT = 0
    # Set up metrics_transformers
    metric_transformers = {}
    DEFAULT_BEARER_TOKEN_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/token'
    DEFAULT_SCHEME = 'https'

    def __init__(self, name, init_config, agentConfig, instances=None):
        # Set up metrics_transformers
        self.metric_transformers = {
                'apiserver_audit_event_total': self.apiserver_audit_event_total,
                'rest_client_requests_total': self.rest_client_requests_total,
                'apiserver_request_count': self.apiserver_request_count,
                'apiserver_dropped_requests_total': self.apiserver_dropped_requests_total,
                'http_requests_total': self.http_requests_total,
                'authenticated_user_requests': self.authenticated_user_requests,
        }
        self.kube_apiserver_config = None

        super(KubeApiserverMetricsCheck, self).__init__(
            name,
            init_config,
            agentConfig,
            instances=instances,
            default_instances={
                "kube_apiserver": {
                    'namespace': 'kube_apiserver',
                    'metrics': [
                        {
                            'apiserver_current_inflight_requests': 'current_inflight_requests',
                            'apiserver_longrunning_gauge': 'longrunning_gauge',
                            'go_threads': 'go_threads',
                            'go_goroutines': 'go_goroutines',
                            'APIServiceRegistrationController_depth': 'APIServiceRegistrationController_depth',
                            'etcd_object_counts': 'etcd_object_counts',
                        }
                    ],
                }
            },
            default_namespace="kube_apiserver",
            )

    def check(self, instance):
        if self.kube_apiserver_config is None:
            kube_apiserver_config =self._create_kube_apiserver_metrics_instance(instance)
            self.kube_apiserver_config = self.get_scraper_config(kube_apiserver_config)

        if not self.kube_apiserver_config['metrics_mapper']:
            raise CheckException(
                 "You have to collect at least one metric from the endpoint: {}".format(scraper_config['prometheus_url'])
            )
        self.process(self.kube_apiserver_config, metric_transformers=self.metric_transformers)

    def _create_kube_apiserver_metrics_instance(self, instance):
        """
        Set up kube_apiserver_metrics instance so it can be used in OpenMetricsBaseCheck
        """
        kube_apiserver_metrics_instance = deepcopy(instance)
        endpoint = instance.get('prometheus_url')
        scheme = instance.get('scheme', self.DEFAULT_SCHEME)

        kube_apiserver_metrics_instance['prometheus_url'] = "{0}://{1}".format(scheme, endpoint)

        bearer_token_path = instance.get('bearer_token_path', self.DEFAULT_BEARER_TOKEN_PATH)
        bearer_token = ""
        try:
            with open(bearer_token_path, "r") as f:
                bearer_token = f.read()
        except Exception as err:
            self.log.warning("Could not retrieve the bearer token file: {}".format(err))

        if bearer_token:
            kube_apiserver_metrics_instance['extra_headers'] = {}
            kube_apiserver_metrics_instance['extra_headers']["Authorization"] = "Bearer {}".format(bearer_token)

        return kube_apiserver_metrics_instance

    def submit_as_gauge_and_monotonic_count(self, metric_suffix, metric, scraper_config):
        """
        submit a kube_apiserver_metrics metric both as a gauge (for compatibility) and as a monotonic_count
        """
        metric_name = scraper_config['namespace'] + metric_suffix
        for sample in metric.samples:
            # Explicit shallow copy of the instance tags
            _tags = list(scraper_config['custom_tags'])

            for label_name, label_value in iteritems(sample[self.SAMPLE_LABELS]):
                _tags.append('{}:{}'.format(label_name, label_value))
            # submit raw metric
            self.gauge(metric_name, sample[self.SAMPLE_VALUE], _tags)
            # submit rate metric
            self.monotonic_count(metric_name + '.count', sample[self.SAMPLE_VALUE], _tags)

    def apiserver_audit_event_total(self, metric, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.audit_event', metric, scraper_config)
    def rest_client_requests_total(self, metric, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.rest_client_requests_total', metric, scraper_config)
    def http_requests_total(self, metric, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.http_requests_total', metric, scraper_config)
    def apiserver_request_count(self, metric, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.apiserver_request_count', metric, scraper_config)
    def apiserver_dropped_requests_total(self, metric, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.apiserver_dropped_requests_total', metric, scraper_config)
    def authenticated_user_requests(self, metric, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.authenticated_user_requests', metric, scraper_config)
