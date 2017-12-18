# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import copy
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest
from checks.prometheus_check import PrometheusCheck

@attr(requires='gitlab_runner')
class TestGitlabRunner(AgentCheckTest):
    """Basic Test for gitlab_runner integration."""
    CHECK_NAME = 'gitlab_runner'
    NAMESPACE = 'gitlab_runner'

    # Note that this is a subset of the ones defined in GitlabRunnerCheck
    # When we stand up a clean test infrastructure some of those metrics might not
    # be available yet, hence we validate a stable subset
    ALLOWED_METRICS = ['ci_runner_errors',
                       'ci_runner_version_info',
                       'process_max_fds',
                       'process_open_fds',
                       'process_resident_memory_bytes',
                       'process_start_time_seconds',
                       'process_virtual_memory_bytes']

    VALID_INSTANCE = {
        'prometheus_endpoint': 'http://localhost:8087/metrics',
        'gitlab_url': 'http://localhost:8085/ci',
        'disable_ssl_validation': True,
    }

    BASE_CONFIG = {
        'init_config': {
            'allowed_metrics': ALLOWED_METRICS
        },
        'instances': [VALID_INSTANCE]
    }

    def test_check(self):
        """
        Testing gitlab_runner check.
        """
        self.run_check(self.BASE_CONFIG)
        for metric in self.ALLOWED_METRICS:
            self.assertMetric("gitlab_runner.%s" % metric)

    def test_connection_success(self):
        self.run_check(self.BASE_CONFIG)

        self.assertServiceCheck('gitlab_runner.can_connect', status=PrometheusCheck.OK,
                                tags=['gitlab_host:localhost', 'gitlab_port:8085'], count=1)

    def test_connection_failure(self):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['gitlab_url'] = 'http://localhost:1234/ci'

        # Assert service check
        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheck('gitlab_runner.can_connect', status=PrometheusCheck.CRITICAL,
                                tags=['gitlab_host:localhost', 'gitlab_port:1234'], count=1)
