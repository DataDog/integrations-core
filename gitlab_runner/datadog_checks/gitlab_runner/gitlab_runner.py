# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import urlparse

# 3rd party
import requests

from datadog_checks.base.errors import CheckException
from datadog_checks.base.checks.prometheus import PrometheusCheck
from datadog_checks.base.config import _is_affirmative
from datadog_checks.base.utils.headers import headers


class GitlabRunnerCheck(PrometheusCheck):
    """
    Collect Gitlab Runner metrics from Prometheus and validates that the connectivity with Gitlab
    """

    EVENT_TYPE = SOURCE_TYPE_NAME = 'gitlab_runner'
    MASTER_SERVICE_CHECK_NAME = 'gitlab_runner.can_connect'
    PROMETHEUS_SERVICE_CHECK_NAME = 'gitlab_runner.prometheus_endpoint_up'

    DEFAULT_CONNECT_TIMEOUT = 5
    DEFAULT_RECEIVE_TIMEOUT = 15
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, agentConfig, instances=None):
        super(GitlabRunnerCheck, self).__init__(name, init_config, agentConfig, instances)
        # Mapping from Prometheus metrics names to Datadog ones
        # For now it's a 1:1 mapping
        # TODO: mark some metrics as rate
        allowed_metrics = init_config.get('allowed_metrics')

        if not allowed_metrics:
            raise CheckException("At least one metric must be whitelisted in `allowed_metrics`.")

        self.metrics_mapper = dict(zip(allowed_metrics, allowed_metrics))
        self.NAMESPACE = 'gitlab_runner'

    def check(self, instance):
        # Metrics collection
        endpoint = instance.get('prometheus_endpoint')
        custom_tags = instance.get('tags', [])
        if endpoint is None:
            raise CheckException("Unable to find prometheus_endpoint in config file.")

        # By default we send the buckets
        send_buckets = _is_affirmative(instance.get('send_histograms_buckets', True))

        try:
            self.process(endpoint, send_histograms_buckets=send_buckets, instance=instance)
            self.service_check(self.PROMETHEUS_SERVICE_CHECK_NAME, PrometheusCheck.OK, tags=custom_tags)
        except requests.exceptions.ConnectionError as e:
            # Unable to connect to the metrics endpoint
            self.service_check(
                self.PROMETHEUS_SERVICE_CHECK_NAME,
                PrometheusCheck.CRITICAL,
                message="Unable to retrieve Prometheus metrics from endpoint {}: {}".format(endpoint, e.message),
                tags=custom_tags,
            )

        # Service check to check whether the Runner can talk to the Gitlab master
        self._check_connectivity_to_master(instance, custom_tags)

    # Validates that the runner can connect to Gitlab
    #
    # Note: Gitlab supports readiness/liveness endpoints but they require an access token
    # or IP whitelisting based on the version
    # https://docs.gitlab.com/ce/user/admin_area/monitoring/health_check.html
    # TODO: consider using those endpoints
    def _check_connectivity_to_master(self, instance, tags):
        url = instance.get('gitlab_url')
        if url is None:
            # Simply ignore this service check if not configured
            return

        parsed_url = urlparse.urlparse(url)
        gitlab_host = parsed_url.hostname
        gitlab_port = 443 if parsed_url.scheme == 'https' else (parsed_url.port or 80)
        service_check_tags = ['gitlab_host:{}'.format(gitlab_host), 'gitlab_port:{}'.format(gitlab_port)]
        service_check_tags.extend(tags)

        # Load the ssl configuration
        ssl_cert_validation = _is_affirmative(instance.get('ssl_cert_validation', True))
        ssl_ca_certs = instance.get('ssl_ca_certs', True)

        verify_ssl = ssl_ca_certs if ssl_cert_validation else False

        # Timeout settings
        timeouts = (
            int(instance.get('connect_timeout', GitlabRunnerCheck.DEFAULT_CONNECT_TIMEOUT)),
            int(instance.get('receive_timeout', GitlabRunnerCheck.DEFAULT_RECEIVE_TIMEOUT)),
        )

        # Auth settings
        auth = None
        if 'gitlab_user' in instance and 'gitlab_password' in instance:
            auth = (instance['gitlab_user'], instance['gitlab_password'])

        try:
            self.log.debug("checking connectivity against {}".format(url))
            r = requests.get(url, auth=auth, verify=verify_ssl, timeout=timeouts, headers=headers(self.agentConfig))
            if r.status_code != 200:
                self.service_check(
                    self.MASTER_SERVICE_CHECK_NAME,
                    PrometheusCheck.CRITICAL,
                    message="Got {} when hitting {}".format(r.status_code, url),
                    tags=service_check_tags,
                )
                raise Exception("Http status code {} on url {}".format(r.status_code, url))
            else:
                r.raise_for_status()

        except requests.exceptions.Timeout:
            # If there's a timeout
            self.service_check(
                self.MASTER_SERVICE_CHECK_NAME,
                PrometheusCheck.CRITICAL,
                message="Timeout when hitting {}".format(url),
                tags=service_check_tags,
            )
            raise
        except Exception as e:
            self.service_check(
                self.MASTER_SERVICE_CHECK_NAME,
                PrometheusCheck.CRITICAL,
                message="Error hitting {}. Error: {}".format(url, e.message),
                tags=service_check_tags,
            )
            raise
        else:
            self.service_check(self.MASTER_SERVICE_CHECK_NAME, PrometheusCheck.OK, tags=service_check_tags)
        self.log.debug("gitlab check succeeded")
