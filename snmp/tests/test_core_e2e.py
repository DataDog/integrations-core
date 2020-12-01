# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict

import pytest

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


def test_e2e_profile(dd_agent_check):
    instance = common.generate_container_profile_instance_config('f5-big-ip')
    assert_python_vs_core(dd_agent_check, instance)


def assert_python_vs_core(dd_agent_check, instance):
    python_instance = instance.copy()
    python_instance['loader'] = 'python'
    core_instance = instance.copy()
    core_instance['loader'] = 'core'
    aggregator = dd_agent_check(python_instance, rate=True)
    expected_metrics = defaultdict(int)
    for _, metrics in aggregator._metrics.items():
        for metric in metrics:
            expected_metrics[(metric.name, metric.type, tuple(sorted(metric.tags)))] += 1

    aggregator.reset()
    aggregator = dd_agent_check(core_instance, rate=True)

    actual_metrics = defaultdict(int)
    for _, metrics in aggregator._metrics.items():
        for metric in metrics:
            actual_metrics[(metric.name, metric.type, tuple(sorted(metric.tags)))] += 1

    print("Python metrics not found in Corecheck metrics")
    for key in expected_metrics:
        (name, mtype, tags) = key
        if has_index_mapping_tag(tags):
            continue
        if key not in actual_metrics:
            print("\t{}".format(key))

    print("Corecheck metrics not found in Python metrics")
    for key in actual_metrics:
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


def has_index_mapping_tag(tags):
    for tag in tags:
        if tag.startswith('ipversion:'):
            return True
    return False
