# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.win.wmi.winwmi_check import WinWMICheck


@pytest.fixture
def check():
    return WinWMICheck("windows_service", {}, {})


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

SERVICE_CHECK_NAME = 'windows_service.state'


class TestWindowsServiceCheck():

    def test_basic_check(self, aggregator, check):
        check.check(INSTANCE)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.OK,
                                        tags=['service:EventLog', 'optional:tag1'], count=1)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.OK,
                                        tags=['service:Dnscache', 'optional:tag1'], count=1)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.CRITICAL,
                                        tags=['service:NonExistingService', 'optional:tag1'], count=1)
        aggregator.assert_all_metrics_covered()

    def test_invalid_host(self, aggregator, check):
        check.check(INVALID_HOST_INSTANCE)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.CRITICAL,
                                        tags=['host:nonexistinghost', 'service:EventLog'], count=1)
        aggregator.assert_all_metrics_covered()

    def test_wildcard(self, aggregator, check):
        check.check(WILDCARD_INSTANCE)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.OK,
                                        tags=['service:EventLog'], count=1)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.OK,
                                        tags=['service:EventSystem'], count=1)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.OK,
                                        tags=['service:Dnscache'], count=1)
        aggregator.assert_all_metrics_covered()

    def test_all(self, aggregator, check):
        check.check(ALL_INSTANCE)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.OK,
                                        tags=['service:EventLog'], count=1)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.OK,
                                        tags=['service:Dnscache'], count=1)
        aggregator.assert_service_check(SERVICE_CHECK_NAME, status=WinWMICheck.OK,
                                        tags=['service:EventSystem'], count=1)
