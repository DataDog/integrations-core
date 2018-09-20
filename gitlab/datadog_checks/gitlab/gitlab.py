# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# stdlib
import urlparse
from copy import deepcopy

# 3rd party
import requests

from datadog_checks.errors import CheckException
from datadog_checks.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.config import _is_affirmative
from datadog_checks.utils.headers import headers


class GitlabCheck(OpenMetricsBaseCheck):
    """
    Collect Gitlab metrics from Prometheus and validates that the connectivity with Gitlab
    """

    # Readiness signals ability to serve traffic, liveness that Gitlab is healthy overall
    ALLOWED_SERVICE_CHECKS = ['readiness', 'liveness']
    EVENT_TYPE = SOURCE_TYPE_NAME = 'gitlab'
    DEFAULT_CONNECT_TIMEOUT = 5
    DEFAULT_RECEIVE_TIMEOUT = 15
    DEFAULT_METRIC_LIMIT = 0

    PROMETHEUS_SERVICE_CHECK_NAME = 'gitlab.prometheus_endpoint_up'

    def __init__(self, name, init_config, agentConfig, instances=None):

        generic_instances = []
        if instances is not None:
            for instance in instances:
                generic_instances.append(self._create_gitlab_prometheus_instance(instance, init_config))

        super(GitlabCheck, self).__init__(name, init_config, agentConfig, instances=generic_instances)

    def check(self, instance):
        # Metrics collection
        endpoint = instance.get('prometheus_endpoint')
        if endpoint is None:
            raise CheckException("Unable to find prometheus_endpoint in config file.")

        scraper_config = self.config_map[endpoint]
        custom_tags = instance.get('tags', [])

        try:
            self.process(scraper_config)
            self.service_check(self.PROMETHEUS_SERVICE_CHECK_NAME, OpenMetricsBaseCheck.OK, tags=custom_tags)
        except requests.exceptions.ConnectionError as e:
            # Unable to connect to the metrics endpoint
            self.service_check(
                self.PROMETHEUS_SERVICE_CHECK_NAME,
                OpenMetricsBaseCheck.CRITICAL,
                message="Unable to retrieve Prometheus metrics from endpoint {}: {}".format(endpoint, e.message),
                tags=custom_tags,
            )

        # Service check to check Gitlab's health endpoints
        for check_type in self.ALLOWED_SERVICE_CHECKS:
            self._check_health_endpoint(instance, check_type, custom_tags)

    def _create_gitlab_prometheus_instance(self, instance, init_config):
        """
        Set up the gitlab instance so it can be used in OpenMetricsBaseCheck
        """
        # Mapping from Prometheus metrics names to Datadog ones
        # For now it's a 1:1 mapping
        allowed_metrics = init_config.get('allowed_metrics')
        if allowed_metrics is None:
            raise CheckException("At least one metric must be whitelisted in `allowed_metrics`.")

        gitlab_instance = deepcopy(instance)
        # gitlab uses 'prometheus_endpoint' and not 'prometheus_url', so we have to rename the key
        gitlab_instance['prometheus_url'] = instance.get('prometheus_endpoint')

        gitlab_instance.update({
            'namespace': 'gitlab',
            'metrics': allowed_metrics,
            # Defaults that were set when gitlab was based on PrometheusCheck
            'send_monotonic_counter': instance.get('send_monotonic_counter', False),
            'health_service_check': instance.get('health_service_check', False)
        })

        return gitlab_instance

    def _verify_ssl(self, instance):
        # Load the ssl configuration
        ssl_cert_validation = _is_affirmative(instance.get('ssl_cert_validation', True))
        ssl_ca_certs = instance.get('ssl_ca_certs', True)

        return ssl_ca_certs if ssl_cert_validation else False

    def _service_check_tags(self, url):
        parsed_url = urlparse.urlparse(url)
        gitlab_host = parsed_url.hostname
        gitlab_port = 443 if parsed_url.scheme == 'https' else (parsed_url.port or 80)
        return ['gitlab_host:{}'.format(gitlab_host), 'gitlab_port:{}'.format(gitlab_port)]

    # Validates an health endpoint
    #
    # Valid endpoints are:
    # - /-/readiness
    # - /-/liveness
    #
    # https://docs.gitlab.com/ce/user/admin_area/monitoring/health_check.html
    def _check_health_endpoint(self, instance, check_type, tags):
        if check_type not in self.ALLOWED_SERVICE_CHECKS:
            raise CheckException("Health endpoint {} is not a valid endpoint".format(check_type))

        url = instance.get('gitlab_url')

        if url is None:
            # Simply ignore this service check if not configured
            self.log.debug("gitlab_url not configured, service check {} skipped".format(check_type))
            return

        service_check_tags = self._service_check_tags(url)
        service_check_tags.extend(tags)
        verify_ssl = self._verify_ssl(instance)

        # Timeout settings
        timeouts = (
            int(instance.get('connect_timeout', GitlabCheck.DEFAULT_CONNECT_TIMEOUT)),
            int(instance.get('receive_timeout', GitlabCheck.DEFAULT_RECEIVE_TIMEOUT)),
        )

        # Auth settings
        auth = None
        if 'gitlab_user' in instance and 'gitlab_password' in instance:
            auth = (instance['gitlab_user'], instance['gitlab_password'])

        # These define which endpoint is hit and which type of check is actually performed
        # TODO: parse errors and report for single sub-service failure?
        service_check_name = 'gitlab.{}'.format(check_type)
        check_url = '{}/-/{}'.format(url, check_type)

        try:
            self.log.debug("checking {} against {}".format(check_type, check_url))
            r = requests.get(
                check_url, auth=auth, verify=verify_ssl, timeout=timeouts, headers=headers(self.agentConfig)
            )
            if r.status_code != 200:
                self.service_check(
                    service_check_name,
                    OpenMetricsBaseCheck.CRITICAL,
                    message="Got {} when hitting {}".format(r.status_code, check_url),
                    tags=service_check_tags,
                )
                raise Exception("Http status code {} on check_url {}".format(r.status_code, check_url))
            else:
                r.raise_for_status()

        except requests.exceptions.Timeout:
            # If there's a timeout
            self.service_check(
                service_check_name,
                OpenMetricsBaseCheck.CRITICAL,
                message="Timeout when hitting {}".format(check_url),
                tags=service_check_tags,
            )
            raise
        except Exception as e:
            self.service_check(
                service_check_name,
                OpenMetricsBaseCheck.CRITICAL,
                message="Error hitting {}. Error: {}".format(check_url, e.message),
                tags=service_check_tags,
            )
            raise
        else:
            self.service_check(service_check_name, OpenMetricsBaseCheck.OK, tags=service_check_tags)
        self.log.debug("gitlab check {} succeeded".format(check_type))
