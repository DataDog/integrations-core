# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import os
import pytest
from datadog_checks.stubs import aggregator
from datadog_checks.aspdotnet import AspdotnetCheck
#import datadog_checks_tests_helper.datadog_test_libs.win
import datadog_test_libs.win.pdh_mocks as mockpdh
HERE = os.path.abspath(os.path.dirname(__file__))
MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE_WITH_TAGS = {
    'host': '.',
    'tags': ['tag1', 'another:tag']
}


@pytest.fixture
def Aggregator():
    aggregator.reset()
    return aggregator


class TestASPDotNet:
    CHECK_NAME = 'aspdotnet'

    # these metrics are single-instance, so they won't have per-instance tags
    ASP_METRICS = (
        "aspdotnet.application_restarts",
        "aspdotnet.worker_process_restarts",
        "aspdotnet.request.wait_time",
    )

    # these metrics are multi-instance.
    ASP_APP_METRICS = (
        # ASP.Net Applications
        "aspdotnet.applications.requests.in_queue",
        "aspdotnet.applications.requests.executing",
        "aspdotnet.applications.requests.persec",
        "aspdotnet.applications.forms_authentication.failure",
        "aspdotnet.applications.forms_authentication.successes",
    )

    ASP_APP_INSTANCES = (
        "__Total__",
        "_LM_W3SVC_1_ROOT_owa_Calendar",
        "_LM_W3SVC_2_ROOT_Microsoft-Server-ActiveSync",
        "_LM_W3SVC_1_ROOT_Microsoft-Server-ActiveSync",
        "_LM_W3SVC_2_ROOT_ecp",
        "_LM_W3SVC_1_ROOT_ecp",
        "_LM_W3SVC_2_ROOT_Rpc",
        "_LM_W3SVC_1_ROOT_Rpc",
        "_LM_W3SVC_2_ROOT_Autodiscover",
        "_LM_W3SVC_1_ROOT_EWS",
        "_LM_W3SVC_2_ROOT_EWS",
        "_LM_W3SVC_1_ROOT_Autodiscover",
        "_LM_W3SVC_1_ROOT_PowerShell",
        "_LM_W3SVC_1_ROOT",
        "_LM_W3SVC_2_ROOT_PowerShell",
        "_LM_W3SVC_1_ROOT_OAB",
        "_LM_W3SVC_2_ROOT_owa",
        "_LM_W3SVC_1_ROOT_owa",
    )

    def _test_basic_check(self, Aggregator):
        instance = MINIMAL_INSTANCE
        c = AspdotnetCheck(self.CHECK_NAME, {}, {}, [instance])
        c.check(instance)

        for metric in self.ASP_METRICS:
            Aggregator.assert_metric(metric, tags=None, count=1)

        for metric in self.ASP_APP_METRICS:
            for i in self.ASP_APP_INSTANCES:
                Aggregator.assert_metric(metric, tags=["instance:%s" % i], count=1)

        assert Aggregator.metrics_asserted_pct == 100.0

    def test_basic_check(self, Aggregator):
        mockpdh.initialize_pdh_tests()
        with mock.patch('_winreg.QueryValueEx', mockpdh.mock_QueryValueEx):
            with mock.patch('win32pdh.LookupPerfNameByIndex', mockpdh.mock_LookupPerfNameByIndex):
                with mock.patch('win32pdh.EnumObjectItems', mockpdh.mock_EnumObjectItems):
                    with mock.patch('win32pdh.MakeCounterPath', mockpdh.mock_MakeCounterPath):
                        with mock.patch('win32pdh.AddCounter', mockpdh.mock_AddCounter):
                            with mock.patch('win32pdh.GetFormattedCounterValue', mockpdh.mock_GetFormattedCounterValue):
                                with mock.patch('win32pdh.CollectQueryData', mockpdh.mock_CollectQueryData):
                                    self._test_basic_check(Aggregator)

    def _test_with_tags(self, Aggregator):
        instance = INSTANCE_WITH_TAGS
        c = AspdotnetCheck(self.CHECK_NAME, {}, {}, [instance])
        c.check(instance)

        for metric in self.ASP_METRICS:
            Aggregator.assert_metric(metric, tags=['tag1', 'another:tag'], count=1)

        for metric in self.ASP_APP_METRICS:
            for i in self.ASP_APP_INSTANCES:
                Aggregator.assert_metric(metric, tags=['tag1', 'another:tag', "instance:%s" % i], count=1)

        assert aggregator.metrics_asserted_pct == 100.0

    def test_with_tags(self, Aggregator):
        mockpdh.initialize_pdh_tests()
        with mock.patch('_winreg.QueryValueEx', mockpdh.mock_QueryValueEx):
            with mock.patch('win32pdh.LookupPerfNameByIndex', mockpdh.mock_LookupPerfNameByIndex):
                with mock.patch('win32pdh.EnumObjectItems', mockpdh.mock_EnumObjectItems):
                    with mock.patch('win32pdh.MakeCounterPath', mockpdh.mock_MakeCounterPath):
                        with mock.patch('win32pdh.AddCounter', mockpdh.mock_AddCounter):
                            with mock.patch('win32pdh.GetFormattedCounterValue', mockpdh.mock_GetFormattedCounterValue):
                                with mock.patch('win32pdh.CollectQueryData', mockpdh.mock_CollectQueryData):
                                    self._test_with_tags(Aggregator)
