# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

RESULTS_TIMEOUT = 20

CONFIG = {
    'init_config': {},
    'instances': [{
        'host': '127.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService'
    }, {
        'host': '126.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService2',
        'tags': ['test1']
    }, {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1.5,
        'name': 'UpService',
        'tags': ['test2']
    }, {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1,
        'name': 'response_time',
        'tags': ['test3'],
        'collect_response_time': True
    }]
}


@attr(requires='tcp_check')
class TCPCheckTest(AgentCheckTest):
    CHECK_NAME = 'tcp_check'

    def tearDown(self):
        self.check.stop()

    def test_check(self):
        """
        Check coverage.
        """
        # Run the check
        self.run_check(CONFIG)

        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', len(CONFIG['instances']), RESULTS_TIMEOUT)
        self.metrics = self.check.get_metrics()

        expected_tags = ["instance:DownService", "target_host:127.0.0.1", "port:65530"]
        self.assertServiceCheckCritical("tcp.can_connect", tags=expected_tags)

        expected_tags = ["instance:DownService2", "target_host:126.0.0.1", "port:65530", "test1"]
        self.assertServiceCheckCritical("tcp.can_connect", tags=expected_tags)

        expected_tags = ["instance:UpService", "target_host:datadoghq.com", "port:80", "test2"]
        self.assertServiceCheckOK("tcp.can_connect", tags=expected_tags)

        expected_tags = ["instance:response_time", "target_host:datadoghq.com", "port:80", "test3"]
        self.assertServiceCheckOK("tcp.can_connect", tags=expected_tags)

        expected_tags = ["instance:response_time", "url:datadoghq.com:80", "test3"]
        self.assertMetric("network.tcp.response_time", tags=expected_tags)

        self.coverage_report()
