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
    # Set up metric_transformers
    METRIC_TRANSFORMERS = {}
    DEFAULT_BEARER_TOKEN_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/token'
    DEFAULT_SCHEME = 'https'

    def __init__(self, name, init_config, agentConfig, instances=None):
        # Set up metric_transformers
        self.METRIC_TRANSFORMERS = {
                'apiserver_audit_event_total': self.apiserver_audit_event_total,
                'rest_client_requests_total': self.rest_client_requests_total,
                'apiserver_request_count': self.apiserver_request_count,
                'apiserver_dropped_requests_total': self.apiserver_dropped_requests_total,
                'http_requests_total': self.http_requests_total,
                'authenticated_user_requests': self.authenticated_user_requests,
        }
        self.bearer_token_found = False
        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        super(KubeApiserverMetricsCheck, self).__init__(
            name,
            init_config,
            agentConfig,
            instances=generic_instances,
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
        if not self.bearer_token_found:
            self.log.warn("Not using the service account bearer token file, AuthN/Z will fail.")
        if not instance.get("prometheus_url"):
            raise ConfigurationError("Missing prometheus_endpoint field. Skipping check")
        scraper_config = self.get_scraper_config(instance)
        self.process(scraper_config, metric_transformers=self.METRIC_TRANSFORMERS)

    def create_generic_instances(self, instances):
        """
        Transform each Kubernetes APIServer endpoint instance into a OpenMetricsBaseCheck instance
        """
        generic_instances = []
        for instance in instances:
            transformed_instance = self._create_kube_apiserver_metrics_instance(instance)
            generic_instances.append(transformed_instance)

        return generic_instances

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
        if not os.path.isfile(bearer_token_path) or not os.access(bearer_token_path, os.R_OK):
            self.bearer_token_found = False
        else:
            with open(bearer_token_path, "r") as f:
                bearer_token = f.read()
        if bearer_token == "":
            self.bearer_token_found = False
        else:
            kube_apiserver_metrics_instance['extra_headers'] = {}
            kube_apiserver_metrics_instance['extra_headers']["Authorization"] = "Bearer {}".format(bearer_token)
            self.bearer_token_found = True

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
