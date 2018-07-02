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
    'tags': ['optional:tag1']
}

INVALID_HOST_INSTANCE = {
    'host': 'nonexistinghost',
    'services': ['EventLog'],
}

WILDCARD_INSTANCE = {
    'host': '.',
    'services': ['Event%', 'Dns%'],
}

ALL_INSTANCE = {
    'host': '.',
    'services': ['ALL'],
}


@attr('windows')
@attr(requires='windows_service')
class TestWindowsService(AgentCheckTest):
    CHECK_NAME = 'windows_service'

    SERVICE_CHECK_NAME = 'windows_service.state'

    def test_basic_check(self):
        self.run_check({'instances': [INSTANCE]})
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:EventLog', 'optional:tag1'], count=1)
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:Dnscache', 'optional:tag1'], count=1)
        self.assertServiceCheckCritical(self.SERVICE_CHECK_NAME, tags=['service:NonExistingService', 'optional:tag1'], count=1)
        self.coverage_report()

    def test_invalid_host(self):
        self.run_check({'instances': [INVALID_HOST_INSTANCE]})
        self.assertServiceCheckCritical(self.SERVICE_CHECK_NAME, tags=['host:nonexistinghost', 'service:EventLog'], count=1)
        self.coverage_report()

    def test_wildcard(self):
        self.run_check({'instances': [WILDCARD_INSTANCE]})
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:EventLog'], count=1)
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:EventSystem'], count=1)
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:Dnscache'], count=1)
        self.coverage_report()

    def test_all(self):
        self.run_check({'instances': [ALL_INSTANCE]})
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:EventLog'], count=1)
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:Dnscache'], count=1)
        self.assertServiceCheckOK(self.SERVICE_CHECK_NAME, tags=['service:EventSystem'], count=1)
        # don't do coverage report as there will be a lot of services we didn't check
        # above.  Just make sure some of the services we know about are present.




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
