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
    python_instance = common.generate_container_instance_config(SUPPORTED_METRIC_TYPES)
    python_instance['loader'] = 'python'
    core_instance = python_instance.copy()
    core_instance['loader'] = 'core'

    print(">>> python instance:", python_instance)
    print(">>> core instance  :", core_instance)

    aggregator = dd_agent_check(python_instance, rate=True)

    expected_metrics = defaultdict(int)
    print(">>> python metrics:")
    for metric_name, metrics in aggregator._metrics.items():
        print("%s: %s".format(metric_name, metrics))
        for metric in metrics:
            expected_metrics[(metric.name, metric.type, tuple(sorted(metric.tags)))] += 1

    aggregator.reset()
    aggregator = dd_agent_check(core_instance, rate=True)

    print(">>> core metrics:")
    for metric_name, metrics in aggregator._metrics.items():
        print("%s: %s".format(metric_name, metrics))

    print(">>> expected metrics:")
    for (name, mtype, tags), count in expected_metrics.items():
        print("metric:", name, mtype, tags, count)
        aggregator.assert_metric(name, metric_type=mtype, tags=tags, count=count)


# def test_e2e_profile(dd_agent_check):
#     python_instance = common.generate_container_profile_instance_config('f5-big-ip')
#     python_instance['loader'] = 'python'
#     core_instance = python_instance.copy()
#     core_instance['loader'] = 'core'
#
#     print(">>> python instance:", python_instance)
#     print(">>> core instance:", core_instance)
#
#     aggregator = dd_agent_check(python_instance, rate=True)
#
#     expected_metrics = defaultdict(int)
#     print(">>> python metrics:")
#     for metric_name, metrics in aggregator._metrics.items():
#         print("metric_name", metric_name)
#         for metric in metrics:
#             expected_metrics[(metric.name, metric.type, tuple(sorted(metric.tags)))] += 1
#
#     aggregator.reset()
#     aggregator = dd_agent_check(core_instance, rate=True)
#
#     print(">>> core metrics:")
#     for metric_name, metrics in aggregator._metrics.items():
#         print("metric_name", metric_name)
#
#     for (name, mtype, tags), count in expected_metrics.items():
#         print("metric:", name, mtype, tags, count)
#         aggregator.assert_metric(name, metric_type=mtype, tags=tags, count=count)
#
#     # Test service check
#     # aggregator.assert_service_check("snmp.can_check", status=SnmpCheck.OK, tags=tags, at_least=1)  # TODO: implement me
#
#     # common.assert_common_metrics(aggregator)
#     # aggregator.all_metrics_asserted()
#
