# stdlib
import urlparse

# 3rd party
import requests

from checks import CheckException
from checks.prometheus_check import PrometheusCheck
from config import _is_affirmative
from util import headers

class GitlabCheck(PrometheusCheck):

    # Readiness signals ability to serve traffic, liveness that Gitlab is healthy overall
    ALLOWED_SERVICE_CHECKS = ['readiness', 'liveness']
    EVENT_TYPE = SOURCE_TYPE_NAME = 'gitlab'
    DEFAULT_CONNECT_TIMEOUT = 5
    DEFAULT_RECEIVE_TIMEOUT = 15

    PROMETHEUS_SERVICE_CHECK_NAME = 'gitlab.prometheus_endpoint_up'

    """
    Collect Gitlab metrics from Prometheus and validates that the connectivity with Gitlab
    """
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(GitlabCheck, self).__init__(name, init_config, agentConfig, instances)
        # Mapping from Prometheus metrics names to Datadog ones
        # For now it's a 1:1 mapping
        # TODO: mark some metrics as rate
        allowed_metrics = init_config.get('allowed_metrics')

        if not allowed_metrics:
            raise CheckException("At least one metric must be whitelisted in `allowed_metrics`.")

        self.metrics_mapper = dict(zip(allowed_metrics, allowed_metrics))
        self.NAMESPACE = 'gitlab'

    def check(self, instance):
        #### Metrics collection
        endpoint = instance.get('prometheus_endpoint')
        if endpoint is None:
            raise CheckException("Unable to find prometheus_endpoint in config file.")

        # By default we send the buckets
        send_buckets = _is_affirmative(instance.get('send_histograms_buckets', True))

        try:
            self.process(endpoint, send_histograms_buckets=send_buckets, instance=instance)
            self.service_check(self.PROMETHEUS_SERVICE_CHECK_NAME, PrometheusCheck.OK)
        except requests.exceptions.ConnectionError as e:
            # Unable to connect to the metrics endpoint
            self.service_check(self.PROMETHEUS_SERVICE_CHECK_NAME, PrometheusCheck.CRITICAL,
                               message="Unable to retrieve Prometheus metrics from endpoint %s: %s" % (endpoint, e.message))

        #### Service check to check Gitlab's health endpoints
        for check_type in self.ALLOWED_SERVICE_CHECKS:
            self._check_health_endpoint(instance, check_type)


    def _verify_ssl(self, instance):
        ## Load the ssl configuration
        ssl_params = {
            'ssl_cert_validation': _is_affirmative(instance.get('ssl_cert_validation', True)),
            'ssl_ca_certs': instance.get('ssl_ca_certs'),
        }

        for key, param in ssl_params.items():
            if param is None:
                del ssl_params[key]

        return ssl_params.get('ssl_ca_certs', True) if ssl_params['ssl_cert_validation'] else False

    def _service_check_tags(self, url):
        parsed_url = urlparse.urlparse(url)
        gitlab_host = parsed_url.hostname
        gitlab_port = 443 if parsed_url.scheme == 'https' else (parsed_url.port or 80)
        return ['gitlab_host:%s' % gitlab_host, 'gitlab_port:%s' % gitlab_port]

    # Validates an health endpoint
    #
    # Valid endpoints are:
    # - /-/readiness
    # - /-/liveness
    #
    # https://docs.gitlab.com/ce/user/admin_area/monitoring/health_check.html
    def _check_health_endpoint(self, instance, check_type):
        if check_type not in self.ALLOWED_SERVICE_CHECKS:
            raise CheckException("Health endpoint %s is not a valid endpoint" % check_type)

        url = instance.get('gitlab_url')
        if url is None:
            # Simply ignore this service check if not configured
            self.log.debug("gitlab_url not configured, service check %s skipped" % check_type)
            return

        service_check_tags = self._service_check_tags(url)
        verify_ssl = self._verify_ssl(instance)

        ## Timeout settings
        timeouts = (int(instance.get('connect_timeout', GitlabCheck.DEFAULT_CONNECT_TIMEOUT)),
                    int(instance.get('receive_timeout', GitlabCheck.DEFAULT_RECEIVE_TIMEOUT)))

        ## Auth settings
        auth = None
        if 'gitlab_user' in instance and 'gitlab_password' in instance:
            auth = (instance['gitlab_user'], instance['gitlab_password'])

        # These define which endpoint is hit and which type of check is actually performed
        # TODO: parse errors and report for single sub-service failure?
        service_check_name = "gitlab.%s" % check_type
        check_url = "%s/-/%s" % (url, check_type)

        try:
            self.log.debug('checking %s against %s' % (check_type, check_url))
            r = requests.get(check_url, auth=auth, verify=verify_ssl, timeout=timeouts,
                             headers=headers(self.agentConfig))
            if r.status_code != 200:
                self.service_check(service_check_name, PrometheusCheck.CRITICAL,
                                   message="Got %s when hitting %s" % (r.status_code, check_url),
                                   tags=service_check_tags)
                raise Exception("Http status code {0} on check_url {1}".format(r.status_code, check_url))
            else:
                r.raise_for_status()

        except requests.exceptions.Timeout:
            # If there's a timeout
            self.service_check(service_check_name, PrometheusCheck.CRITICAL,
                               message="Timeout when hitting %s" % check_url,
                               tags=service_check_tags)
            raise
        except Exception as e:
            self.service_check(service_check_name, PrometheusCheck.CRITICAL,
                               message="Error hitting %s. Error: %s" % (check_url, e.message),
                               tags=service_check_tags)
            raise
        else:
            self.service_check(service_check_name, PrometheusCheck.OK, tags=service_check_tags)
        self.log.debug("gitlab check %s succeeded" % check_type)
