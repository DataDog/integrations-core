# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy
import os
from six import iteritems

from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck

class KubeApiserverMetricsCheck(OpenMetricsBaseCheck):
    """
    Collect kubernetes apiserver metrics in the Prometheus format
    See https://github.com/kubernetes/apiserver
    """
    DEFAULT_METRIC_LIMIT = 0
    # Set up metric_transformers
    METRIC_TRANSFORMERS = {}
    DEFAULT_BEARER_TOKEN_PATH = '/var/run/secrets/kubernets.io/serviceaccount/token'
    DEFAULT_SCHEME = 'https'

    def __init__(self, name, init_config, agentConfig, instances=None):
        # Set up metric_transformers
        self.METRIC_TRANSFORMERS = {
                'apiserver_audit_event_total': self.apiserver_audit_event_total,
        }
        # Create instances we can use in OpenMetricsBaseCheck
        generic_instances = None
        if instances is not None:
            generic_instances = self.create_generic_instances(instances)

        super(KubeApiserverMetricsCheck, self).__init__(name, init_config, agentConfig, instances=generic_instances)

    def check(self, instance):
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
        endpoint = instance.get('prometheus_endpoint', None)
        scheme = instance.get('scheme', self.DEFAULT_SCHEME)
        bearer_token_path = instance.get('bearer_token_path', self.DEFAULT_BEARER_TOKEN_PATH)

        if not os.path.isfile(bearer_token_path) or not os.access(bearer_token_path, os.R_OK):
            # log a warn if the bearer_token_path is unavailable
            self.log.warn("Unable to read service account bearer token file at %s" % (bearer_token_path))
        else:
            with open(bearer_token_path, "r") as f:
                bearer_token = f.read()
        if bearer_token == "":
            self.log.warn("No bearer token available in %s. Service account might be misconfigured. Attempting to run the check without AuthN/Z", bearer_token_path)
        else:
            kube_apiserver_metrics_instance['extra_headers'] = {}
            kube_apiserver_metrics_instance['extra_headers']["Authorization"] = "Bearer {}".format(bearer_token)
         
        kube_apiserver_metrics_instance['prometheus_url'] = "{0}://{1}".format(scheme, endpoint)

        kube_apiserver_metrics_instance.update(
            {
                'namespace': 'kubeapiserver',
                # Note: the count metrics were moved to specific functions list below to be submitted
                # as both gauges and monotonic_counts
                'metrics': [
                    {
                        'apiserver_client_certificate_expiration_seconds': 'apiserver_client_certificate_expiration',
                        'apiserver_current_inflight_requests': 'apiserver_current_inflight_requests',
                        'apiserver_longrunning_gauge': 'apiserver_longrunning_gauge',
                    }
                ],
            }
        )
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
        self.submit_as_gauge_and_monotonic_count('.audit_event_count', metric, scraper_config)