# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import os
import pytest
import re
import string
import _winreg
from collections import defaultdict
from datadog_checks.stubs import aggregator
from datadog_checks.aspdotnet import AspdotnetCheck

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



counters_by_class = defaultdict(set)
instances_by_class = defaultdict(set)
def read_available_counters(fname):
    counters_by_class.clear()
    instances_by_class.clear()
    regex = r'(\\[^(]+)(?:\(([^)]+)\))?(\\[^(]+)'
    compiled_regex = re.compile(regex)

    with open(os.path.join(HERE, 'fixtures', 'allcounters.txt')) as f:
        for line in f:
            line = line.rstrip()
            clss, inst, counter = [x if not x else x.lstrip('\\') for x in compiled_regex.search(line).groups()]
            counters_by_class[clss].add(counter)
            if inst:
                instances_by_class[clss].add(inst)

def mock_EnumObjectItems(reserved, machine_name, clss, detail):
    ctrs = list(counters_by_class[clss])
    insts = list(instances_by_class[clss])
    return ctrs, insts

def mock_MakeCounterPath(machine, clss, inst, parent, iindex, cname):
    ## do some sanity checking
    if clss not in counters_by_class:
        raise AttributeError("class name {} is invalid".format(clss))
    if inst and inst not in instances_by_class[clss]:
        raise AttributeError("instance name {} is invalid".format(inst))
    if cname not in counters_by_class[clss]:
        raise AttributeError("class name {} is invalid".format(cname))

    if inst:
        p = "%s|%s|%s" % (clss, inst, cname)
    else:
        p = "%s| |%s" % (clss, cname)
    return p

def mock_AddCounter(h, path):
    return path

def mock_GetFormattedCounterValue(h, p):
    return 1, 0 # for now

def mock_CollectQueryData(h):
    return True


## need to mock
## _winreg.QueryValueEx(_winreg.HKEY_PERFORMANCE_DATA, "Counter 009")
##
index_array = []
counters_index = defaultdict(list)
def load_registry_values():
    global index_array
    index_array = []
    counters_index.clear()

    with open(os.path.join(HERE, 'fixtures', 'counter_indexes_en.txt')) as f:
        linecount = 0
        for line in f:
            line = string.strip(line)
            if not line or len(line) == 0:
                if linecount % 2 == 0:
                    break
                line = " "

            index_array.append(line)
            linecount += 1

    idx = 0
    idx_max = len(index_array)
    while idx < idx_max:
        index = int(index_array[idx])
        c = index_array[idx + 1]
        counters_index[int(index_array[idx])] = index_array[idx+1]
        idx += 2

def mock_QueryValueEx(*args, **kwargs):
    return (index_array, _winreg.REG_SZ)


def mock_LookupPerfNameByIndex(machine_name, ndx):
    return counters_index[ndx]

'''
@pytest.fixture(scope="module")
def reg_mocks():
    load_registry_values()
    p1 = mock.patch('_winreg.QueryValueEx', mock_QueryValueEx,
                    __name__="QueryValueEx")

    #p2 = mock.patch('psutil.disk_usage', return_value=MockDiskMetrics(),
    #                __name__="disk_usage")
    #p3 = mock.patch('os.statvfs', return_value=MockInodesMetrics(),
    #                __name__="statvfs")
    #p4 = mock.patch('psutil.disk_io_counters', return_value=MockDiskIOMetrics())

    yield p1.start() ##, p2.start(), p3.start(), p4.start()

    p1.stop()
    #p2.stop()
    #p3.stop()
    #p4.stop()
'''
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
        load_registry_values()
        read_available_counters(None)
        with mock.patch('_winreg.QueryValueEx', mock_QueryValueEx):
            with mock.patch('win32pdh.LookupPerfNameByIndex', mock_LookupPerfNameByIndex):
                with mock.patch('win32pdh.EnumObjectItems', mock_EnumObjectItems):
                    with mock.patch('win32pdh.MakeCounterPath', mock_MakeCounterPath):
                        with mock.patch('win32pdh.AddCounter', mock_AddCounter):
                            with mock.patch('win32pdh.GetFormattedCounterValue', mock_GetFormattedCounterValue):
                                with mock.patch('win32pdh.CollectQueryData', mock_CollectQueryData):
                                    self._test_basic_check(Aggregator)

    def _test_with_tags(self, Aggregator):
        load_registry_values()
        read_available_counters(None)
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
        load_registry_values()
        read_available_counters(None)
        with mock.patch('_winreg.QueryValueEx', mock_QueryValueEx):
            with mock.patch('win32pdh.LookupPerfNameByIndex', mock_LookupPerfNameByIndex):
                with mock.patch('win32pdh.EnumObjectItems', mock_EnumObjectItems):
                    with mock.patch('win32pdh.MakeCounterPath', mock_MakeCounterPath):
                        with mock.patch('win32pdh.AddCounter', mock_AddCounter):
                            with mock.patch('win32pdh.GetFormattedCounterValue', mock_GetFormattedCounterValue):
                                with mock.patch('win32pdh.CollectQueryData', mock_CollectQueryData):
                                    self._test_with_tags(Aggregator)
