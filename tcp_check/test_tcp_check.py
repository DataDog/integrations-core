# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlibb
import time

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

RESULTS_TIMEOUT = 40

CONFIG = {
    'init_config': {},
    'instances': [{
        'host': '127.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService',
        'skip_event': True
    }, {
        'host': '126.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService2',
        'tags': ['test1'],
        'skip_event': True
    }, {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1.5,
        'name': 'UpService',
        'tags': ['test2'],
        'skip_event': True
    }, {
        'host': 'datadoghq.com',
        'port': 80,
        'timeout': 1,
        'name': 'response_time',
        'tags': ['test3'],
        'collect_response_time': True,
        'skip_event': True
    }]
}

CONFIG_EVENTS = {
    'init_config': {},
    'instances': [{
        'host': '127.0.0.1',
        'port': 65530,
        'timeout': 1.5,
        'name': 'DownService',
        'skip_event': False
    }]
}


@attr(requires='tcp_check')
class TCPCheckTest(AgentCheckTest):
    CHECK_NAME = 'tcp_check'

    def tearDown(self):
        self.check.stop()

    def wait_for_async(self, method, attribute, count):
        """
        Loop on `self.check.method` until `self.check.attribute >= count`.

        Raise after
        """

        # Check the initial values to see if we already have results before waiting for the async
        # instances to finish
        initial_values = getattr(self, attribute)

        i = 0
        while i < RESULTS_TIMEOUT:
            self.check._process_results()
            if len(getattr(self.check, attribute)) + len(initial_values) >= count:
                return getattr(self.check, method)() + initial_values
            time.sleep(1.1)
            i += 1
        raise Exception("Didn't get the right count of service checks in time, {0}/{1} in {2}s: {3}"
                        .format(len(getattr(self.check, attribute)), count, i,
                                getattr(self.check, attribute)))

    def test_event_deprecation(self):
        """
        Deprecate events usage for service checks.
        """
        # Run the check
        self.run_check(CONFIG_EVENTS)

        # Overrides self.service_checks attribute when values are available
        self.warnings = self.wait_for_async('get_warnings', 'warnings', len(CONFIG_EVENTS['instances']))

        # Assess warnings
        self.assertWarning(
            "Using events for service checks is deprecated in "
            "favor of monitors and will be removed in future versions of the "
            "Datadog Agent.",
            count=len(CONFIG_EVENTS['instances'])
        )

    def test_check(self):
        """
        Check coverage.
        """
        # Run the check
        self.run_check(CONFIG)

        # Overrides self.service_checks attribute when values are available
        self.service_checks = self.wait_for_async('get_service_checks', 'service_checks', len(CONFIG['instances']))
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
