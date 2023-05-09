# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple
from types import SimpleNamespace

import mock
import pytest

from datadog_checks.nvml import NvmlCheck


class MockNvml:
    @staticmethod
    def is_nvml_library_available(i):
        return True

    @staticmethod
    def nvmlInit():
        pass

    @staticmethod
    def nvmlShutdown():
        pass

    @staticmethod
    def nvmlDeviceGetHandleByIndex(i):
        return "test-handle"

    @staticmethod
    def nvmlDeviceGetCount():
        return 1

    @staticmethod
    def nvmlDeviceGetUUID(h):
        return str.encode("test-guid")

    @staticmethod
    def nvmlDeviceGetUtilizationRates(h):
        return SimpleNamespace(gpu=2, memory=3)

    @staticmethod
    def nvmlDeviceGetMemoryInfo(h):
        return SimpleNamespace(free=40, used=50, total=90)

    @staticmethod
    def nvmlDeviceGetPowerUsag3(h):
        return 7

    @staticmethod
    def nvmlDeviceGetTotalEnergyConsumption(h):
        return 8

    @staticmethod
    def nvmlDeviceGetEncoderUtilization(h):
        return (9, 0)

    @staticmethod
    def nvmlDeviceGetDecoderUtilization(h):
        return (10, 0)

    @staticmethod
    def nvmlDeviceGetPcieThroughput(h, b):
        return 11

    @staticmethod
    def nvmlDeviceGetPowerUsage(h):
        return 12

    @staticmethod
    def nvmlDeviceGetTemperature(h, b):
        return 13

    @staticmethod
    def nvmlDeviceGetFanSpeed(h):
        return 14

    @staticmethod
    def nvmlDeviceGetComputeRunningProcesses_v2(h):
        Mock = namedtuple('Mock', ['pid', 'usedGpuMemory'])
        return [Mock(pid=1, usedGpuMemory=11)]


@pytest.mark.unit
def test_check(aggregator, instance):
    with mock.patch('datadog_checks.nvml.NvmlCheck.N', MockNvml):
        check = NvmlCheck('nvml', {}, [instance])
        check.check(instance)
    expected_tags = ["gpu:0"]
    aggregator.assert_metric('nvml.device_count', count=1)
    aggregator.assert_metric('nvml.gpu_utilization', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.mem_copy_utilization', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.total_energy_consumption', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.fb_free', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.fb_used', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.fb_total', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.enc_utilization', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.dec_utilization', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.pcie_rx_throughput', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.pcie_tx_throughput', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.power_usage', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.temperature', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.fan_speed', tags=expected_tags, count=1)
    aggregator.assert_metric('nvml.compute_running_process', tags=expected_tags + ["pid:1"], count=1)

    aggregator.assert_all_metrics_covered()
