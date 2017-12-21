# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from nose.plugins.attrib import attr

# project
from checks import AgentCheck
from tests.checks.common import AgentCheckTest
from tests.core.test_wmi import TestCommonWMI

INSTANCE = {
    'host': '.',
    'services': ['EventLog', 'Dnscache', 'NonExistingService'],
}

INVALID_HOST_INSTANCE = {
    'host': 'nonexistinghost',
    'services': ['EventLog'],
}

@attr('windows')
@attr(requires='windows_service')
class TestWindowsService(AgentCheckTest):
    CHECK_NAME = 'windows_service'

    SERVICE_CHECK_NAME = 'windows_service.state'

    def test_basic_check(self):
        self.run_check({'instances': [INSTANCE]})
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:EventLog'], count=1)
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:Dnscache'], count=1)
        self.assertServiceCheckCritical(self.SERVICE_CHECK_NAME, tags=['service:NonExistingService'], count=1)
        self.coverage_report()

    def test_invalid_host(self):
        self.run_check({'instances': [INVALID_HOST_INSTANCE]})
        self.assertServiceCheckCritical(self.SERVICE_CHECK_NAME, tags=['host:nonexistinghost', 'service:EventLog'], count=1)
        self.coverage_report()


class WindowsServiceTestCase(AgentCheckTest, TestCommonWMI):
    CHECK_NAME = 'windows_service'

    WIN_SERVICES_CONFIG = {
        'host': ".",
        'services': ["WinHttpAutoProxySvc", "WSService"]
    }

    def test_check(self):
        """
        Returns the right service checks
        """
        # Run check
        config = {
            'instances': [self.WIN_SERVICES_CONFIG]
        }

        self.run_check(config)

        # Test service checks
        self.assertServiceCheck('windows_service.state', status=AgentCheck.OK, count=1,
                                tags=[u'service:WinHttpAutoProxySvc'])
        self.assertServiceCheck('windows_service.state', status=AgentCheck.CRITICAL, count=1,
                                tags=[u'service:WSService'])

        self.coverage_report()
