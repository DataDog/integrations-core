# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from mock import patch

from datadog_checks.wmi_check import WMICheck


@pytest.fixture
def check():
    return WMICheck('wmi_check', {}, {}, None)


class MockSampler():
    def __init__(self, wmi_objects=[], properties=[], filters=[]):
        self._wmi_objects = []
        self._mock_wmi_objects = wmi_objects
        self.property_names = properties
        self._filters = []

        self.connection = {}

    def __getitem__(self, i):
        return self._wmi_objects[i]

    def __iter__(self):
        for wmi_object in self._wmi_objects:
            yield wmi_object

    def __len__(self):
        return len(self._wmi_objects)

    def sample(self):
        self._wmi_objects = self._mock_wmi_objects

    def reset(self):
        self._wmi_objects = []

    def reset_filter(self, new_filters=None):
        pass


@pytest.fixture
def mock_proc_sampler():
    WMI_Mock = [{
        "IOReadBytesPerSec": 20455,
        "IDProcess": 4036,
        "ThreadCount": 4,
        "VirtualBytes": 3811,
        "PercentProcessorTime": 5,
    }]
    property_names = [
        "ThreadCount",
        "IOReadBytesPerSec",
        "VirtualBytes",
        "PercentProcessorTime"
    ]
    sampler = MockSampler(WMI_Mock, property_names)

    with patch("datadog_checks.wmi_check.WMICheck._get_wmi_sampler", return_value=sampler):
        yield


@pytest.fixture
def mock_disk_sampler():
    WMI_Mock = [{
        "AvgDiskBytesPerWrite": 1536,
        "FreeMegabytes": 19742,
    }]
    property_names = [
        "AvgDiskBytesPerWrite",
        "FreeMegabytes",
    ]
    sampler = MockSampler(WMI_Mock, property_names)

    with patch("datadog_checks.wmi_check.WMICheck._get_wmi_sampler", return_value=sampler):
        yield
