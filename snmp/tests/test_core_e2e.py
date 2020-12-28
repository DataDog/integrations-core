# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict
from copy import deepcopy

import pytest

from datadog_checks.base.stubs.common import MetricStub

from . import common

pytestmark = [pytest.mark.e2e, common.python_autodiscovery_only]

SUPPORTED_METRIC_TYPES = [
    {'MIB': 'ABC', 'symbol': {'OID': "1.3.6.1.2.1.7.1.0", 'name': "IAmACounter32"}},  # Counter32
    {'MIB': 'ABC', 'symbol': {'OID': "1.3.6.1.2.1.4.31.1.1.6.1", 'name': "IAmACounter64"}},  # Counter64
    {'MIB': 'ABC', 'symbol': {'OID': "1.3.6.1.2.1.4.24.6.0", 'name': "IAmAGauge32"}},  # Gauge32
    {'MIB': 'ABC', 'symbol': {'OID': "1.3.6.1.2.1.88.1.1.1.0", 'name': "IAmAnInteger"}},  # Integer
]


def test_e2e_metric_types(dd_agent_check):
    instance = common.generate_container_instance_config(SUPPORTED_METRIC_TYPES)
    assert_python_vs_core(dd_agent_check, instance)


def test_e2e_profile_f5(dd_agent_check):
    config = common.generate_container_profile_config('f5-big-ip')
    assert_python_vs_core(dd_agent_check, config, total_count=469)


def test_e2e_profile_cisco_nexus(dd_agent_check):
    config = common.generate_container_profile_config('cisco-nexus')
    assert_python_vs_core(dd_agent_check, config, total_count=469)


METRIC_TO_SKIP = [
    # forced_type: percent
    'snmp.sysMultiHostCpuUser',
    'snmp.sysMultiHostCpuNice',
    'snmp.sysMultiHostCpuSystem',
    'snmp.sysMultiHostCpuIdle',
    'snmp.sysMultiHostCpuIrq',
    'snmp.sysMultiHostCpuSoftirq',
    'snmp.sysMultiHostCpuIowait',
    # bandwidth
    'snmp.ifBandwidthInUsage.rate',
    'snmp.ifBandwidthOutUsage.rate',
    # telemetry
    'snmp.check_duration',
    'snmp.check_interval',
    'snmp.submitted_metrics',
]


def assert_python_vs_core(dd_agent_check, config, total_count=None):
    python_config = deepcopy(config)
    python_config['init_config']['loader'] = 'python'
    core_config = deepcopy(config)
    core_config['init_config']['loader'] = 'core'
    aggregator = dd_agent_check(python_config, rate=True)
    expected_metrics = defaultdict(int)
    for _, metrics in aggregator._metrics.items():
        for stub in metrics:
            if stub.name in METRIC_TO_SKIP:
                continue
            assert "loader:core" not in stub.tags
            stub = normalize_stub_metric(stub)
            expected_metrics[(stub.name, stub.type, tuple(sorted(stub.tags)))] += 1
    expected_count = sum(count for count in expected_metrics.values())

    aggregator.reset()
    aggregator = dd_agent_check(core_config, rate=True)

    aggregator_metrics = aggregator._metrics
    aggregator._metrics = defaultdict(list)
    for metric_name in aggregator_metrics:
        for stub in aggregator_metrics[metric_name]:
            assert "loader:core" in stub.tags
            if stub.name in METRIC_TO_SKIP:
                continue
            aggregator._metrics[metric_name].append(normalize_stub_metric(stub))

    actual_metrics = defaultdict(int)
    for _, metrics in aggregator._metrics.items():
        for metric in metrics:
            actual_metrics[(metric.name, metric.type, tuple(sorted(metric.tags)))] += 1

    print("Python metrics not found in Corecheck metrics:")
    for key in sorted(expected_metrics):
        (name, mtype, tags) = key
        if has_index_mapping_tag(tags):
            continue
        if key not in actual_metrics:
            print("\t{}".format(key))

    print("Corecheck metrics not found in Python metrics:")
    for key in sorted(actual_metrics):
        (name, mtype, tags) = key
        if has_index_mapping_tag(tags):
            continue
        if key not in expected_metrics:
            print("\t{}".format(key))

    for (name, mtype, tags), count in expected_metrics.items():
        # TODO: to delete when index mapping support is added to corecheck snmp
        if has_index_mapping_tag(tags):
            aggregator.assert_metric(name, metric_type=mtype)
            continue
        aggregator.assert_metric(name, metric_type=mtype, tags=tags, count=count)

    aggregator.assert_all_metrics_covered()

    # assert count
    actual_count = sum(len(metrics) for metrics in aggregator._metrics.values())
    assert expected_count == actual_count
    if total_count is not None:
        assert total_count == actual_count == expected_count


def normalize_stub_metric(stub):
    tags = [t for t in stub.tags if not t.startswith('loader:')]  # Remove `loader` tag
    return MetricStub(
        stub.name,
        stub.type,
        stub.value,
        tags,
        stub.hostname,
        stub.device,
    )


def has_index_mapping_tag(tags):
    for tag in tags:
        if tag.startswith('ipversion:'):
            return True
    return False
