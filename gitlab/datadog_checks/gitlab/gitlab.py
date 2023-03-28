# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import requests
from six import PY2

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.errors import CheckException, ConfigurationError

from .common import get_gitlab_version, get_tags
from .metrics import METRICS_MAP


class GitlabCheck(OpenMetricsBaseCheck):
    """
    Collect Gitlab metrics from Prometheus and validates that the connectivity with Gitlab
    """

    # Readiness signals ability to serve traffic, liveness that Gitlab is healthy overall
    ALLOWED_SERVICE_CHECKS = ['readiness', 'liveness', 'health']
    EVENT_TYPE = SOURCE_TYPE_NAME = 'gitlab'
    DEFAULT_CONNECT_TIMEOUT = 5
    DEFAULT_RECEIVE_TIMEOUT = 15
    DEFAULT_METRIC_LIMIT = 0

    PROMETHEUS_SERVICE_CHECK_NAME = 'gitlab.prometheus_endpoint_up'

    HTTP_CONFIG_REMAPPER = {
        'receive_timeout': {'name': 'read_timeout', 'default': DEFAULT_RECEIVE_TIMEOUT},
        'connect_timeout': {'name': 'connect_timeout', 'default': DEFAULT_CONNECT_TIMEOUT},
        'gitlab_user': {'name': 'username'},
        'gitlab_password': {'name': 'password'},
        'ssl_cert_validation': {'name': 'tls_verify'},
        'ssl_ca_certs': {'name': 'tls_ca_cert'},
    }

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if instance.get('openmetrics_endpoint'):
            if PY2:
                raise ConfigurationError(
                    'This version of the integration is only available when using Python 3. '
                    'Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3/ '
                    'for more information or use the older style config.'
                )
            # TODO: when we drop Python 2 move this import up top
            from .gitlab_v2 import GitlabCheckV2

            return GitlabCheckV2(name, init_config, instances)

        return super(GitlabCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(GitlabCheck, self).__init__(
            name, init_config, [self._create_gitlab_prometheus_instance(instances[0], init_config)]
        )

        self.endpoint = self.instance.get('prometheus_url', self.instance.get('prometheus_endpoint'))
        if self.endpoint is None:
            raise CheckException("Unable to find `prometheus_url` or `prometheus_endpoint` in config file.")

        self.url = self.instance.get('gitlab_url', None)
        self.token = self.instance.get('api_token', None)

    def check(self, _):
        scraper_config = self.config_map[self.endpoint]

        try:
            self.process(scraper_config)
            self.service_check(self.PROMETHEUS_SERVICE_CHECK_NAME, OpenMetricsBaseCheck.OK, self._tags)
        except requests.exceptions.ConnectionError as e:
            # Unable to connect to the metrics endpoint
            self.service_check(
                self.PROMETHEUS_SERVICE_CHECK_NAME,
                OpenMetricsBaseCheck.CRITICAL,
                self._tags,
                message="Unable to retrieve Prometheus metrics from endpoint {}: {}".format(self.endpoint, e),
            )

        # Service check to check Gitlab's health endpoints
        for check_type in self.ALLOWED_SERVICE_CHECKS:
            self._check_health_endpoint(check_type)

        self.submit_version()

    def _create_gitlab_prometheus_instance(self, instance, init_config):
        """
        Set up the gitlab instance so it can be used in OpenMetricsBaseCheck
        """
        # Mapping from Gitlab specific Prometheus metric names to Datadog ones
        metrics = [METRICS_MAP]

        # Add allowed legacy metrics
        metrics.extend(init_config.get('allowed_metrics', []))

        gitlab_instance = deepcopy(instance)
        # gitlab uses 'prometheus_endpoint' and not 'prometheus_url', so we have to rename the key
        gitlab_instance['prometheus_url'] = instance.get('prometheus_url', instance.get('prometheus_endpoint'))

        self._tags = get_tags(gitlab_instance)

        gitlab_instance.update(
            {
                'namespace': 'gitlab',
                'metrics': metrics,
                'send_distribution_counts_as_monotonic': instance.get('send_distribution_counts_as_monotonic', True),
                'send_distribution_sums_as_monotonic': instance.get('send_distribution_sums_as_monotonic', True),
                'send_monotonic_counter': instance.get('send_monotonic_counter', True),
                'health_service_check': instance.get('health_service_check', False),
                'tags': self._tags,
            }
        )

        return gitlab_instance

    @AgentCheck.metadata_entrypoint
    def submit_version(self):
        version = get_gitlab_version(self.http, self.log, self.url, self.token)

        if version:
            self.log.debug("Set version %s for GitLab", version)
            self.set_metadata("version", version)

    # Validates an health endpoint
    #
    # Valid endpoints are:
    # - /-/readiness
    # - /-/liveness
    # - /-/health
    #
    # https://docs.gitlab.com/ce/user/admin_area/monitoring/health_check.html
    def _check_health_endpoint(self, check_type):
        if check_type not in self.ALLOWED_SERVICE_CHECKS:
            raise CheckException("Health endpoint {} is not a valid endpoint".format(check_type))

        if self.url is None:
            # Simply ignore this service check if not configured
            self.log.debug("gitlab_url not configured, service check %s skipped", check_type)
            return

        # These define which endpoint is hit and which type of check is actually performed
        # TODO: parse errors and report for single sub-service failure?
        service_check_name = 'gitlab.{}'.format(check_type)
        check_url = '{}/-/{}'.format(self.url, check_type)

        try:
            self.log.debug("checking %s against %s", check_type, check_url)
            r = self.http.get(check_url)
            if r.status_code != 200:
                self.service_check(
                    service_check_name,
                    OpenMetricsBaseCheck.CRITICAL,
                    message="Got {} when hitting {}".format(r.status_code, check_url),
                    tags=self._tags,
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
                tags=self._tags,
            )
            raise
        except Exception as e:
            self.service_check(
                service_check_name,
                OpenMetricsBaseCheck.CRITICAL,
                message="Error hitting {}. Error: {}".format(check_url, e),
                tags=self._tags,
            )
            raise

        else:
            self.service_check(service_check_name, OpenMetricsBaseCheck.OK, self._tags)
        self.log.debug("gitlab check %s succeeded", check_type)
