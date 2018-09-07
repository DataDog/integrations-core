# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.windows_service import WindowsService


@pytest.fixture
def check():
    return WindowsService("windows_service", {}, {}, None)


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

ALL_STATES_INSTANCE = {
    "host": ".",
    "services": [
        "StoppedService", "StartPendingService", "StopPendingService", "RunningService",
        "ContinuePendingService", "PausePendingService", "PausedService", "UnknownService"
    ]
}


class mock_sampler():
    def __init__(self):
        self._wmi_objects = []

    def __getitem__(self, i):
        return self._wmi_objects[i]

    def sample(self):
        self._wmi_objects = [
            {
                "Name": "StoppedService",
                "state": "Stopped"
            },
            {
                "Name": "StartPendingService",
                "state": "Start Pending"
            },
            {
                "Name": "StopPendingService",
                "state": "Stop Pending"
            },
            {
                "Name": "RunningService",
                "state": "Running"
            },
            {
                "Name": "ContinuePendingService",
                "state": "Continue Pending"
            },
            {
                "Name": "PausePendingService",
                "state": "Pause Pending"
            },
            {
                "Name": "PausedService",
                "state": "Paused"
            },
            {
                "Name": "UnknownService",
                "state": "Unknown"
            },
        ]

    def reset(self):
        self._wmi_objects = []


def test_basic_check(aggregator, check):
    check.check(INSTANCE)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=['service:EventLog', 'optional:tag1'], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=['service:Dnscache', 'optional:tag1'], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.CRITICAL,
                                    tags=['service:NonExistingService', 'optional:tag1'], count=1)
    aggregator.assert_all_metrics_covered()


def test_invalid_host(aggregator, check):
    check.check(INVALID_HOST_INSTANCE)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.CRITICAL,
                                    tags=['host:nonexistinghost', 'service:EventLog'], count=1)
    aggregator.assert_all_metrics_covered()


def test_wildcard(aggregator, check):
    check.check(WILDCARD_INSTANCE)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=['service:EventLog'], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=['service:EventSystem'], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=['service:Dnscache'], count=1)
    aggregator.assert_all_metrics_covered()


def test_all(aggregator, check):
    check.check(ALL_INSTANCE)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=['service:EventLog'], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=['service:Dnscache'], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=['service:EventSystem'], count=1)


def test_service_states(aggregator, check, mocker):
    mocker.patch("datadog_checks.windows_service.WindowsService._get_wmi_sampler", return_value=mock_sampler())
    check.check(ALL_STATES_INSTANCE)

    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.CRITICAL,
                                    tags=["service:StoppedService"], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.WARNING,
                                    tags=["service:StartPendingService"], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.WARNING,
                                    tags=["service:StopPendingService"], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.OK,
                                    tags=["service:RunningService"], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.WARNING,
                                    tags=["service:ContinuePendingService"], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.WARNING,
                                    tags=["service:PausePendingService"], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.WARNING,
                                    tags=["service:PausedService"], count=1)
    aggregator.assert_service_check(WindowsService.SERVICE_CHECK_NAME, status=WindowsService.UNKNOWN,
                                    tags=["service:UnknownService"], count=1)
