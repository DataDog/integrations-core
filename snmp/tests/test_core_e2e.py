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
    assert_python_vs_core(dd_agent_check, config, expected_total_count=28)


def test_e2e_profile_chatsworth_pdu(dd_agent_check):
    config = common.generate_container_profile_config('chatsworth_pdu')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=184)


def test_e2e_profile_checkpoint_firewall(dd_agent_check):
    config = common.generate_container_profile_config('checkpoint-firewall')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=301)


def test_e2e_profile_cisco_3850(dd_agent_check):
    config = common.generate_container_profile_config('cisco-3850')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=4290)


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
    assert_python_vs_core(dd_agent_check, config)


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


METRIC_TO_SKIP = [
    # wrong mac_addr value
    # python: ('snmp.cswSwitchState', 0, ('device_vendor:cisco', 'mac_addr:0xffffffffffff',
    #          'snmp_device:172.24.0.2', 'snmp_host:Nexus-eu1.companyname.managed', 'snmp_profile:cisco-nexus'))
    # core:   ('snmp.cswSwitchState', 0, ('device_vendor:cisco', 'mac_addr:....', 'snmp_device:172.24.0.2',
    #          'snmp_host:Nexus-eu1.companyname.managed', 'snmp_profile:cisco-nexus'))
    #         ('snmp.cpiPduChainRole', 0, ('device_vendor:chatsworth', 'legacy_pdu_macaddress:00:0E:D3:AA:CC:EE',
    #          'legacy_pdu_model:P10-1234-ABC', 'legacy_pdu_name:legacy-name1', 'legacy_pdu_version:1.2.3',
    #          'pdu_cabinetid:cab1', 'pdu_macaddress:\\x0...., 'pdu_model:model1', 'pdu_name:name1',
    #          'pdu_version:v1.1', 'snmp_device:172.24.0.2', 'snmp_profile:chatsworth_pdu'))
    'snmp.cswSwitchState',
    'snmp.cpiPduChainRole',
    'snmp.cpiPduNumberBranches',
    'snmp.cpiPduNumberOutlets',
    'snmp.cpiPduOutOfService',
    'snmp.cpiPduTotalPower',
    'snmp.cpiPduUpgrade',
    # handle metrics present multiple times. Example:
    # - snmp.memoryDeviceStatus
    # - snmp.networkDeviceStatus
    # from dell-poweredge.yaml and _dell-rac.yaml
    'snmp.networkDeviceStatus',
    'snmp.memoryDeviceStatus',
    # handle gosnmp.IPAddress and gosnmp.ObjectIdentifier:
    # https://github.com/DataDog/datadog-agent/blob/c2dac4ee5d83cf4a2d2616c5fed409e1c075c2fa/pkg/collector/corechecks/snmp/gosnmp_value.go#L9-L30
    'snmp.bgpPeerAdminStatus',
    'snmp.bgpPeerConnectRetryInterval',
    'snmp.bgpPeerFsmEstablishedTime',
    'snmp.bgpPeerFsmEstablishedTransitions',
    'snmp.bgpPeerHoldTime',
    'snmp.bgpPeerHoldTimeConfigured',
    'snmp.bgpPeerInTotalMessages',
    'snmp.bgpPeerInUpdates',
    'snmp.bgpPeerKeepAlive',
    'snmp.bgpPeerKeepAliveConfigured',
    'snmp.bgpPeerMinASOriginationInterval',
    'snmp.bgpPeerNegotiatedVersion',
    'snmp.bgpPeerOutTotalMessages',
    'snmp.bgpPeerOutUpdates',
    'snmp.bgpPeerRemoteAs',
    'snmp.bgpPeerState',
    # handle old symbol syntax. Example:
    'snmp.cfInterconnectStatus',
    'snmp.extcache64Hits',
    'snmp.miscCacheAge',
    'snmp.ncHttpActiveCliConns',
    # snmpsim type 64x
    'snmp.ospfIfLsaCount',
    'snmp.ospfIfRetransInterval',
    'snmp.ospfIfState',
    'snmp.ospfNbrEvents',
    'snmp.ospfNbrLsRetransQLen',
    'snmp.ospfNbrState',
    'snmp.ospfVirtIfLsaCount',
    'snmp.ospfVirtIfRetransInterval',
    'snmp.ospfVirtIfState',
    'snmp.ospfVirtNbrEvents',
    'snmp.ospfVirtNbrLsRetransQLen',
    'snmp.ospfVirtNbrState',
    # index_transform
    'snmp.cpiPduBranchCurrent',
    'snmp.cpiPduBranchEnergy',
    'snmp.cpiPduBranchMaxCurrent',
    'snmp.cpiPduBranchPower',
    'snmp.cpiPduBranchPowerFactor',
    'snmp.cpiPduBranchStatus',
    'snmp.cpiPduBranchVoltage',
    # bandwidth
    'snmp.ifBandwidthInUsage.rate',
    'snmp.ifBandwidthOutUsage.rate',
    # telemetry
    'snmp.check_duration',
    'snmp.check_interval',
    'snmp.submitted_metrics',
]


def assert_python_vs_core(dd_agent_check, config, expected_total_count=None):
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
    total_count_python = sum(count for count in expected_metrics.values())

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
    total_count_corecheck = sum(len(metrics) for metrics in aggregator._metrics.values())
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


def has_index_mapping_tag(tags):
    for tag in tags:
        if tag.startswith('ipversion:'):
            return True
    return False
