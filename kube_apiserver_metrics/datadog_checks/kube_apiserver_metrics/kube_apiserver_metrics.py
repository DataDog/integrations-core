# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from re import match

from six import iteritems

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.errors import CheckException


class KubeAPIServerMetricsCheck(OpenMetricsBaseCheck):
    """
    Collect kubernetes apiserver metrics in the Prometheus format
    See https://github.com/kubernetes/apiserver
    """

    DEFAULT_METRIC_LIMIT = 0
    # Set up metrics_transformers
    metric_transformers = {}
    DEFAULT_SCHEME = 'https'
    DEFAULT_SSL_VERIFY = False
    DEFAULT_BEARER_TOKEN_AUTH = True

    def __init__(self, name, init_config, instances=None):
        # Set up metrics_transformers
        self.metric_transformers = {
            'apiserver_audit_event_total': self.apiserver_audit_event_total,
            'rest_client_requests_total': self.rest_client_requests_total,
            'apiserver_request_count': self.apiserver_request_count,
            'apiserver_dropped_requests_total': self.apiserver_dropped_requests_total,
            'http_requests_total': self.http_requests_total,
            'authenticated_user_requests': self.authenticated_user_requests,
            # metric added in kubernetes 1.15
            'apiserver_request_total': self.apiserver_request_total,
        }
        self.kube_apiserver_config = None

        super(KubeAPIServerMetricsCheck, self).__init__(
            name,
            init_config,
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
            self.kube_apiserver_config = self.get_scraper_config(instance)

        if not self.kube_apiserver_config['metrics_mapper']:
            url = self.kube_apiserver_config['prometheus_url']
            raise CheckException("You have to collect at least one metric from the endpoint: {}".format(url))
        self.process(self.kube_apiserver_config, metric_transformers=self.metric_transformers)

    def get_scraper_config(self, instance):
        # Change config before it's cached by parent get_scraper_config
        config = self._create_kube_apiserver_metrics_instance(instance)
        return super(KubeAPIServerMetricsCheck, self).get_scraper_config(config)

    def _create_kube_apiserver_metrics_instance(self, instance):
        """
        Set up kube_apiserver_metrics instance so it can be used in OpenMetricsBaseCheck
        """
        kube_apiserver_metrics_instance = deepcopy(instance)
        endpoint = instance.get('prometheus_url')
        prometheus_url = endpoint

        # Allow using a proper URL without introducing a breaking change since
        # the scheme option is deprecated.
        if not match('^https?://.*$', endpoint):
            scheme = instance.get('scheme', self.DEFAULT_SCHEME)
            prometheus_url = "{0}://{1}".format(scheme, endpoint)

        kube_apiserver_metrics_instance['prometheus_url'] = prometheus_url

        # Most set ups are using self signed certificates as the APIServer can be used as a CA.
        ssl_verify = instance.get('ssl_verify', self.DEFAULT_SSL_VERIFY)
        kube_apiserver_metrics_instance['ssl_verify'] = ssl_verify

        # We should default to supporting environments using RBAC to access the APIServer.
        bearer_token_auth = instance.get('bearer_token_auth', self.DEFAULT_BEARER_TOKEN_AUTH)
        kube_apiserver_metrics_instance['bearer_token_auth'] = bearer_token_auth

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

    def apiserver_request_total(self, metric, scraper_config):
        self.submit_as_gauge_and_monotonic_count('.apiserver_request_total', metric, scraper_config)
