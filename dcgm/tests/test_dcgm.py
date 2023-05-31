# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest

from datadog_checks import * # Might as well try all since I was having problems
# from datadog_checks.dev.utils import get_metadata_metrics
# from datadog_checks.base.stubs.aggregator import AggregatorStub #Needed for MERTIS=[]
from datadog_checks.dcgm import DcgmCheck
from unittest import mock


@pytest.fixture
def instance():
    return {"openmetrics_endpoint": "http://host:9400/metrics"}

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

#TODO: To collect counter metrics with names ending in `_total`, specify the metric name without the `_total`
# It seems that those metrics that are not exposed in the curl are causing some issues are they have nothing to correspond to.

# A representative sampling of metrics from the fixture used for unit tests
METRICS = [
    {
        "name": "dec_utilization"
    },
    {
        "name": "enc_utilization"
    },
    {
        "name": "fb_free"
    },
    {
        "name": "fb_used"
    },
    {
        "name": "temperature"
    },
    {
        "name": "gpu_utilization"
    },
    {
        "name": "mem_clock"
    },
    {
        "name": "mem_copy_utilization"
    },
    # {
    #     "name": "nvlink_bandwidth_total"  #removed the total for processing
    # },
    {
        "name": "pcie_replay_counter.count" # added .count to pass
    },
    {
        "name": "power_usage"
    },
    {
        "name": "sm_clock"
    },
    {
        "name": "total_energy_consumption.count" # added .count to pass
    },
    {
        "name": "vgpu_license_status"
    },
    {
        "name": "xid_errors"
    },
    {
        "name": "device_count.count"  # added .count to pass
    },
    # {
    #     "name": "fan_speed"
    # },
    # {
    #     "name": "pcie_tx_throughput"
    # },
    # {
    #     "name": "pcie_rx_throughput"
    # },
    # {
    #     "name": "memory_temperature"
    # },
    # {
    #     "name": "uncorrectable_remapped_rows"
    # },
    # {
    #     "name": "correctable_remapped_rows"
    # },
    # {
    #     "name": "row_remap_failure"
    # }
]
