# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from unittest import mock

import pytest

from datadog_checks.dcgm import DcgmCheck


@pytest.fixture
def instance():
    return {"openmetrics_endpoint": "http://localhost:9400/metrics"}


@pytest.fixture
def check(instance):
    return DcgmCheck('dcgm.', {}, [instance])


@pytest.fixture()
def mock_metrics():
    f_name = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


def test_check(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=f"dcgm.{expected_metric['name']}",
        )


def test_service_checks(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)
    aggregator.assert_service_check('dcgm.openmetrics.health', DcgmCheck.OK)


# A representative sampling of metrics from the fixture used for unit tests
METRICS = [
    {"name": "dec_utilization"},
    {"name": "enc_utilization"},
    {"name": "fb_free"},
    {"name": "fb_used"},
    {"name": "temperature"},
    {"name": "gpu_utilization"},
    {"name": "mem_clock"},
    {"name": "mem_copy_utilization"},
    {"name": "nvlink_bandwidth.count"},
    {"name": "pcie_replay_counter.count"},
    {"name": "power_usage"},
    {"name": "sm_clock"},
    {"name": "total_energy_consumption.count"},
    {"name": "vgpu_license_status"},
    {"name": "xid_errors"},
    {"name": "device_count.count"},
]
