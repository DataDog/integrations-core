# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import copy
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest
from checks.prometheus_check import PrometheusCheck

@attr(requires='gitlab')
class TestGitlab(AgentCheckTest):
    """Basic Test for gitlab integration."""
    CHECK_NAME = 'gitlab'
    NAMESPACE = 'gitlab'

    # Note that this is a subset of the ones defined in GitlabCheck
    # When we stand up a clean test infrastructure some of those metrics might not
    # be available yet, hence we validate a stable subset
    ALLOWED_METRICS = ['process_max_fds',
                       'process_open_fds',
                       'process_resident_memory_bytes',
                       'process_start_time_seconds',
                       'process_virtual_memory_bytes']

    VALID_INSTANCE = {
        'prometheus_endpoint': 'http://localhost:8088/metrics',
        'gitlab_url': 'http://localhost:8086',
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
        Testing gitlab check.
        """
        self.run_check(self.BASE_CONFIG)
        for metric in self.ALLOWED_METRICS:
            self.assertMetric("gitlab.%s" % metric)

    def test_service_checks_success(self):
        self.run_check(self.BASE_CONFIG)

        self.assertServiceCheck('gitlab.readiness', status=PrometheusCheck.OK,
                                tags=['gitlab_host:localhost', 'gitlab_port:8086'], count=1)

        self.assertServiceCheck('gitlab.liveness', status=PrometheusCheck.OK,
                                tags=['gitlab_host:localhost', 'gitlab_port:8086'], count=1)

    def test_connection_failure(self):
        config = copy.deepcopy(self.BASE_CONFIG)
        config['instances'][0]['gitlab_url'] = 'http://localhost:1234/ci'

        # Assert service check
        self.assertRaises(
            Exception,
            lambda: self.run_check(config)
        )
        self.assertServiceCheck('gitlab.readiness', status=PrometheusCheck.CRITICAL,
                                tags=['gitlab_host:localhost', 'gitlab_port:1234'], count=1)
