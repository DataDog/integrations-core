# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from copy import deepcopy

import requests
from six.moves.urllib.parse import urlparse

from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck
from datadog_checks.base.errors import CheckException


class GitlabRunnerCheck(OpenMetricsBaseCheck):
    """
    Collect Gitlab Runner metrics from Prometheus and validates that the connectivity with Gitlab
    """

    EVENT_TYPE = SOURCE_TYPE_NAME = 'gitlab_runner'
    MASTER_SERVICE_CHECK_NAME = 'gitlab_runner.can_connect'
    PROMETHEUS_SERVICE_CHECK_NAME = 'gitlab_runner.prometheus_endpoint_up'

    DEFAULT_CONNECT_TIMEOUT = 5
    DEFAULT_RECEIVE_TIMEOUT = 15
    DEFAULT_METRIC_LIMIT = 0

    HTTP_CONFIG_REMAPPER = {
        'receive_timeout': {'name': 'read_timeout', 'default': DEFAULT_RECEIVE_TIMEOUT},
        'connect_timeout': {'name': 'connect_timeout', 'default': DEFAULT_CONNECT_TIMEOUT},
        'gitlab_user': {'name': 'username'},
        'gitlab_password': {'name': 'password'},
        'ssl_cert_validation': {'name': 'tls_verify'},
        'ssl_ca_certs': {'name': 'tls_ca_cert'},
    }

    def __init__(self, name, init_config, instances):
        super(GitlabRunnerCheck, self).__init__(
            name, init_config, [self._create_gitlab_runner_prometheus_instance(instances[0], init_config)]
        )

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
                message="Unable to retrieve Prometheus metrics from endpoint {}: {}".format(endpoint, e),
                tags=custom_tags,
            )

        # Service check to check whether the Runner can talk to the Gitlab master
        self._check_connectivity_to_master(instance, custom_tags)

    def _create_gitlab_runner_prometheus_instance(self, instance, init_config):
        """
        Set up the gitlab_runner instance so it can be used in OpenMetricsBaseCheck
        """
        # Mapping from Prometheus metrics names to Datadog ones
        # For now it's a 1:1 mapping
        allowed_metrics = init_config.get('allowed_metrics')
        if allowed_metrics is None:
            raise CheckException("At least one metric must be whitelisted in `allowed_metrics`.")

        gitlab_runner_instance = deepcopy(instance)

        # gitlab_runner uses 'prometheus_endpoint' and not 'prometheus_url', so we have to rename the key
        gitlab_runner_instance['prometheus_url'] = instance.get('prometheus_endpoint', None)

        gitlab_runner_instance.update(
            {
                'namespace': 'gitlab_runner',
                'metrics': allowed_metrics,
                # Defaults that were set when gitlab_runner was based on PrometheusCheck
                'send_monotonic_counter': instance.get('send_monotonic_counter', False),
                'health_service_check': instance.get('health_service_check', False),
            }
        )

        return gitlab_runner_instance

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

        parsed_url = urlparse(url)
        gitlab_host = parsed_url.hostname
        gitlab_port = 443 if parsed_url.scheme == 'https' else (parsed_url.port or 80)
        service_check_tags = ['gitlab_host:{}'.format(gitlab_host), 'gitlab_port:{}'.format(gitlab_port)]
        service_check_tags.extend(tags)

        try:
            self.log.debug("checking connectivity against %s", url)
            r = self.http.get(url)
            if r.status_code != 200:
                self.service_check(
                    self.MASTER_SERVICE_CHECK_NAME,
                    OpenMetricsBaseCheck.CRITICAL,
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
                OpenMetricsBaseCheck.CRITICAL,
                message="Timeout when hitting {}".format(url),
                tags=service_check_tags,
            )
            raise
        except Exception as e:
            self.service_check(
                self.MASTER_SERVICE_CHECK_NAME,
                OpenMetricsBaseCheck.CRITICAL,
                message="Error hitting {}. Error: {}".format(url, e),
                tags=service_check_tags,
            )
            raise
        else:
            self.service_check(self.MASTER_SERVICE_CHECK_NAME, OpenMetricsBaseCheck.OK, tags=service_check_tags)
        self.log.debug("gitlab check succeeded")
