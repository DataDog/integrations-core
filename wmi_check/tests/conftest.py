# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from unittest.mock import MagicMock

import pytest
from mock import patch

from datadog_checks.wmi_check import WMICheck


@pytest.fixture
def check():
    return lambda instance: WMICheck('wmi_check', {}, [instance])


class MockSampler:
    def __init__(self, wmi_objects=None, properties=None, filters=None):
        if wmi_objects is None:
            wmi_objects = []
        if properties is None:
            properties = []

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
    WMI_Mock = [
        {
            "IOReadBytesPerSec": 20455,
            "IDProcess": 4036,
            "ThreadCount": 4,
            "VirtualBytes": 3811,
            "PercentProcessorTime": 5,
        }
    ]
    property_names = ["ThreadCount", "IOReadBytesPerSec", "VirtualBytes", "PercentProcessorTime"]
    sampler = MockSampler(WMI_Mock, property_names)

    with patch("datadog_checks.wmi_check.WMICheck._get_running_wmi_sampler", return_value=sampler):
        yield


@pytest.fixture
def mock_disk_sampler():
    WMI_Mock = [{"AvgDiskBytesPerWrite": 1536, "FreeMegabytes": 19742}]
    property_names = ["AvgDiskBytesPerWrite", "FreeMegabytes"]
    sampler = MockSampler(WMI_Mock, property_names)

    with patch("datadog_checks.wmi_check.WMICheck._get_running_wmi_sampler", return_value=sampler):
        yield


@pytest.fixture
def mock_sampler_with_tag_queries():
    # Main sampler with IDProcess for tag queries
    main_wmi_objects = [
        {
            "IOReadBytesPerSec": 20455,
            "IDProcess": 1234,
            "ThreadCount": 4,
            "VirtualBytes": 3811,
            "PercentProcessorTime": 5,
        }
    ]
    main_property_names = ["ThreadCount", "IOReadBytesPerSec", "VirtualBytes", "PercentProcessorTime", "IDProcess"]
    main_sampler = MockSampler(main_wmi_objects, main_property_names)
    main_sampler.class_name = 'Win32_PerfFormattedData_PerfProc_Process'

    # Tag query sampler for process names
    tag_wmi_objects = [{'Name': 'chrome.exe'}]
    tag_property_names = ['Name']
    tag_sampler = MockSampler(tag_wmi_objects, tag_property_names)
    tag_sampler.class_name = 'Win32_Process'
    tag_sampler.sample()  # Populate the mock data

    with patch("datadog_checks.wmi_check.WMICheck._get_running_wmi_sampler", return_value=main_sampler):
        with patch("datadog_checks.base.checks.win.wmi.base.WMISampler") as mock_wmi_sampler:
            # Setup context manager to return tag_sampler for tag queries
            mock_wmi_sampler.return_value.__enter__ = MagicMock(return_value=tag_sampler)
            mock_wmi_sampler.return_value.__exit__ = MagicMock(return_value=False)
            yield


@pytest.fixture
def mock_sampler_with_tag_by_prefix():
    main_wmi_objects = [
        {
            "IOReadBytesPerSec": 20455,
            "IDProcess": 1234,
            "Name": "chrome.exe",
            "ThreadCount": 4,
            "VirtualBytes": 3811,
            "PercentProcessorTime": 5,
        }
    ]
    main_property_names = [
        "ThreadCount",
        "IOReadBytesPerSec",
        "VirtualBytes",
        "PercentProcessorTime",
        "IDProcess",
        "Name",
    ]
    main_sampler = MockSampler(main_wmi_objects, main_property_names)
    main_sampler.class_name = 'Win32_PerfFormattedData_PerfProc_Process'

    with patch("datadog_checks.wmi_check.WMICheck._get_running_wmi_sampler", return_value=main_sampler):
        yield
