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


CORECHECK_ONLY_METRICS = [
    'datadog.snmp.check_duration',
    'datadog.snmp.check_interval',
    'datadog.snmp.submitted_metrics',
]


def test_e2e_metric_types(dd_agent_check):
    instance = common.generate_container_instance_config(SUPPORTED_METRIC_TYPES)
    assert_python_vs_core(dd_agent_check, instance, expected_total_count=10)


def test_e2e_v3(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['instances'][0].update(
        {
            'user': 'datadogSHADES',
            'authKey': 'doggiepass',
            'authProtocol': 'sha',
            'privKey': 'doggiePRIVkey',
            'privProtocol': 'des',
            'snmp_version': 3,
            'context_name': 'f5-big-ip',
            'community_string': '',
        }
    )
    assert_python_vs_core(dd_agent_check, config, expected_total_count=489)


def test_e2e_regex_match(dd_agent_check):
    metrics = [
        {
            'MIB': "IF-MIB",
            'table': {
                "name": "ifTable",
                "OID": "1.3.6.1.2.1.2.2",
            },
            'symbols': [
                {
                    "name": "ifInOctets",
                    "OID": "1.3.6.1.2.1.2.2.1.10",
                },
                {
                    "name": "ifOutOctets",
                    "OID": "1.3.6.1.2.1.2.2.1.16",
                },
            ],
            'metric_tags': [
                {
                    'tag': "interface",
                    'column': {
                        "name": "ifDescr",
                        "OID": "1.3.6.1.2.1.2.2.1.2",
                    },
                },
                {
                    'column': {
                        "name": "ifDescr",
                        "OID": "1.3.6.1.2.1.2.2.1.2",
                    },
                    'match': '(\\w)(\\w+)',
                    'tags': {'prefix': '\\1', 'suffix': '\\2'},
                },
            ],
        }
    ]
    config = common.generate_container_instance_config(metrics)
    config['instances'][0]['metric_tags'] = [
        {
            "OID": "1.3.6.1.2.1.1.5.0",
            "symbol": "sysName",
            "match": "(\\d+)(\\w+)",
            "tags": {
                "digits": "\\1",
                "remainder": "\\2",
            },
        },
        {
            "OID": "1.3.6.1.2.1.1.5.0",
            "symbol": "sysName",
            "match": "(\\w)(\\w)",
            "tags": {
                "letter1": "\\1",
                "letter2": "\\2",
            },
        },
    ]
    assert_python_vs_core(dd_agent_check, config)

    config['init_config']['loader'] = 'core'
    aggregator = dd_agent_check(config, rate=True)

    # raw sysName: 41ba948911b9
    aggregator.assert_metric(
        'snmp.devices_monitored',
        tags=[
            'digits:41',
            'remainder:ba948911b9',
            'letter1:4',
            'letter2:1',
            'snmp_device:172.18.0.2',
        ],
    )


def test_e2e_scalar_oid_retry(dd_agent_check):
    scalar_objects_with_tags = [
        {'OID': "1.3.6.1.2.1.7.1", 'name': "udpDatagrams"},
    ]
    instance = common.generate_container_instance_config(scalar_objects_with_tags)
    assert_python_vs_core(dd_agent_check, instance)


def test_e2e_symbol_metric_tags(dd_agent_check):
    scalar_objects_with_tags = [
        {'OID': "1.3.6.1.2.1.7.1.0", 'name': "udpDatagrams", 'metric_tags': ['udpdgrams', 'UDP']},
        {'OID': "1.3.6.1.2.1.6.10.0", 'name': "tcpInSegs", 'metric_tags': ['tcpinsegs', 'TCP']},
    ]
    instance = common.generate_container_instance_config(scalar_objects_with_tags)
    assert_python_vs_core(dd_agent_check, instance)


# Profile tests
# expected_total_count: Test with some expected_total_count to be sure that both python and corecheck impl
# are collecting some metrics.


def test_e2e_profile_apc_ups(dd_agent_check):
    config = common.generate_container_profile_config('apc_ups')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=42)


def test_e2e_profile_arista(dd_agent_check):
    config = common.generate_container_profile_config('arista')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=14)


def test_e2e_profile_aruba(dd_agent_check):
    config = common.generate_container_profile_config('aruba')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=67)


def test_e2e_profile_chatsworth_pdu(dd_agent_check):
    config = common.generate_container_profile_config('chatsworth_pdu')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=225)


def test_e2e_profile_checkpoint_firewall(dd_agent_check):
    config = common.generate_container_profile_config('checkpoint-firewall')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=301)


def test_e2e_profile_cisco_3850(dd_agent_check):
    config = common.generate_container_profile_config('cisco-3850')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=4554)


def test_e2e_profile_cisco_asa(dd_agent_check):
    config = common.generate_container_profile_config('cisco-asa')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_cisco_asa_5525(dd_agent_check):
    config = common.generate_container_profile_config('cisco-asa-5525')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_cisco_catalyst(dd_agent_check):
    config = common.generate_container_profile_config('cisco-catalyst')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_cisco_csr1000v(dd_agent_check):
    config = common.generate_container_profile_config('cisco-csr1000v')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_cisco_nexus(dd_agent_check):
    config = common.generate_container_profile_config('cisco-nexus')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_cisco_icm(dd_agent_check):
    config = common.generate_container_profile_config('cisco_icm')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_dell_poweredge(dd_agent_check):
    config = common.generate_container_profile_config('dell-poweredge')

    # TODO: Fix python implementation for duplicate declarations
    metric_to_skip = [
        # Following metrics are declared multiple times in profiles.
        # Example: snmp.networkDeviceStatus and snmp.memoryDeviceStatus are declared twice
        # in dell-poweredge.yaml and _dell-rac.yaml
        # This is causing python impl to not behave correctly. Some `snmp.networkDeviceStatus` doesn't include
        # either `ip_address` or `chassis_index/mac_addr/device_fqdd` tags.
        # See II-153
        'snmp.networkDeviceStatus',
        'snmp.memoryDeviceStatus',
    ]
    assert_python_vs_core(dd_agent_check, config, metrics_to_skip=metric_to_skip)


def test_e2e_profile_f5_big_ip(dd_agent_check):
    config = common.generate_container_profile_config('f5-big-ip')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_fortinet_fortigate(dd_agent_check):
    config = common.generate_container_profile_config('fortinet-fortigate')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_generic_router(dd_agent_check):
    config = common.generate_container_profile_config('generic-router')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_hp_ilo4(dd_agent_check):
    config = common.generate_container_profile_config('hp-ilo4')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_hpe_proliant(dd_agent_check):
    config = common.generate_container_profile_config('hpe-proliant')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_idrac(dd_agent_check):
    config = common.generate_container_profile_config('idrac')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_isilon(dd_agent_check):
    config = common.generate_container_profile_config('isilon')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_meraki_cloud_controller(dd_agent_check):
    config = common.generate_container_profile_config('meraki-cloud-controller')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_netapp(dd_agent_check):
    config = common.generate_container_profile_config('netapp')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_palo_alto(dd_agent_check):
    config = common.generate_container_profile_config('palo-alto')
    assert_python_vs_core(dd_agent_check, config)


ASSERT_VALUE_METRICS = []


def assert_python_vs_core(dd_agent_check, config, expected_total_count=None, metrics_to_skip=None):
    python_config = deepcopy(config)
    python_config['init_config']['loader'] = 'python'
    core_config = deepcopy(config)
    core_config['init_config']['loader'] = 'core'
    aggregator = dd_agent_check(python_config, rate=True)
    expected_metrics = defaultdict(list)
    metrics_to_skip = metrics_to_skip or []
    for _, metrics in aggregator._metrics.items():
        for stub in metrics:
            if stub.name in metrics_to_skip:
                continue
            stub = normalize_stub_metric(stub)
            expected_metrics[(stub.name, stub.type, tuple(sorted(stub.tags)))].append(stub)

    expected_sc = defaultdict(list)
    for _, service_checks in aggregator._service_checks.items():
        for stub in service_checks:
            expected_sc[(stub.name, stub.status, tuple(sorted(stub.tags)), stub.message)].append(stub)

    total_count_python = sum(len(stubs) for stubs in expected_metrics.values())

    aggregator.reset()
    aggregator = dd_agent_check(core_config, rate=True)

    aggregator_metrics = aggregator._metrics
    aggregator._metrics = defaultdict(list)
    for metric_name in aggregator_metrics:
        for stub in aggregator_metrics[metric_name]:
            if stub.name in metrics_to_skip:
                continue
            aggregator._metrics[metric_name].append(normalize_stub_metric(stub))

    actual_metrics = defaultdict(list)
    for _, metrics in aggregator._metrics.items():
        for metric in metrics:
            actual_metrics[(metric.name, metric.type, tuple(sorted(metric.tags)))].append(metric)

    print("Python metrics not found in Corecheck metrics:")
    for key in sorted(expected_metrics):
        if key not in actual_metrics:
            print("\t{}".format(key))

    print("Corecheck metrics not found in Python metrics:")
    print(
        "(expected to be listed here: datadog.snmp.check_duration, datadog.snmp.check_interval, "
        "datadog.snmp.submitted_metrics)"
    )
    for key in sorted(actual_metrics):
        if key not in expected_metrics:
            print("\t{}".format(key))

    for (name, mtype, tags), stubs in expected_metrics.items():
        if name in ASSERT_VALUE_METRICS:
            for stub in stubs:
                aggregator.assert_metric(name, metric_type=mtype, tags=tags, count=len(stubs), value=stub.value)
        else:
            aggregator.assert_metric(name, metric_type=mtype, tags=tags, count=len(stubs))

    for metric in CORECHECK_ONLY_METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()

    for (name, status, tags, message), stubs in expected_sc.items():
        aggregator.assert_service_check(name, status, tags, count=len(stubs), message=message)

    # assert count
    total_count_corecheck = sum(
        len(metrics) for key, metrics in aggregator._metrics.items() if key not in CORECHECK_ONLY_METRICS
    )
    assert total_count_python == total_count_corecheck
    if expected_total_count is not None:
        assert expected_total_count == total_count_corecheck


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
