# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.snmp import SnmpCheck
from datadog_checks.snmp.utils import (
    _get_profile_name,
    _is_abstract_profile,
    _iter_default_profile_file_paths,
    get_profile_definition,
    recursively_expand_base_profiles,
)

from . import common, metrics
from .metrics import (
    ADAPTER_IF_COUNTS,
    CCCA_ROUTER_GAUGES,
    CIE_METRICS,
    COS_COUNTS,
    COS_RATES,
    CPU_METRICS,
    DCU_COUNTS,
    DISK_GAUGES,
    DRS_GAUGES,
    FIREWALL_COUNTS,
    FRU_METRICS,
    IDRAC_SYSTEM_STATUS_GAUGES,
    IF_BANDWIDTH_USAGE,
    IF_COUNTS,
    IF_GAUGES,
    IF_RATES,
    IF_SCALAR_GAUGE,
    IP_COUNTS,
    IP_IF_COUNTS,
    IPX_COUNTS,
    LTM_GAUGES,
    LTM_NODES_COUNTS,
    LTM_NODES_GAUGES,
    LTM_NODES_RATES,
    LTM_POOL_COUNTS,
    LTM_POOL_GAUGES,
    LTM_POOL_MEMBER_COUNTS,
    LTM_POOL_MEMBER_GAUGES,
    LTM_POOL_MEMBER_RATES,
    LTM_POOL_RATES,
    LTM_VIRTUAL_SERVER_COUNTS,
    LTM_VIRTUAL_SERVER_GAUGES,
    LTM_VIRTUAL_SERVER_RATES,
    MEMORY_METRICS,
    PEER_GAUGES,
    PEER_RATES,
    POWEREDGE_SYSTEM_STATUS_GAUGES,
    PROBE_GAUGES,
    SCU_COUNTS,
    TCP_COUNTS,
    TCP_GAUGES,
    UDP_COUNTS,
    USER_FIREWALL,
    VIRTUAL_CHASSIS_COUNTS,
    VIRTUAL_CHASSIS_RATES,
    VOLTAGE_GAUGES,
)

pytestmark = common.snmp_integration_only


def test_load_profiles(caplog):
    instance = common.generate_instance_config([])
    check = SnmpCheck('snmp', {}, [instance])
    caplog.at_level(logging.WARNING)
    for name, profile in check.profiles.items():
        try:
            check._config.refresh_with_profile(profile)
        except ConfigurationError as e:
            pytest.fail("Profile `{}` is not configured correctly: {}".format(name, e))
        assert "table doesn't have a 'metric_tags' section" not in caplog.text
        caplog.clear()


def test_profile_hierarchy():
    """
    * Abstract profile must not define a `sysobjectid` field.
    """
    errors = []

    for path in _iter_default_profile_file_paths():
        name = _get_profile_name(path)
        definition = get_profile_definition({'definition_file': path})
        sysobjectid = definition.get('sysobjectid')

        if _is_abstract_profile(name):
            if sysobjectid is not None:
                errors.append("'{}': mixin wrongly defines a `sysobjectid`".format(name))

    if errors:
        pytest.fail('\n'.join(sorted(errors)))


def run_profile_check(recording_name, profile_name=None):
    """
    Run a single check with the provided `recording_name` used as
    `community_string` by the docker SNMP endpoint.
    """

    instance = common.generate_instance_config([])

    instance['community_string'] = recording_name
    instance['enforce_mib_constraints'] = False
    # if a profile_name is specified, use that profile
    if profile_name is not None:
        instance['profile'] = profile_name
    check = SnmpCheck('snmp', {}, [instance])
    check.check(instance)


@pytest.mark.unit
@pytest.mark.parametrize(
    'definition_file, equivalent_definition',
    [
        pytest.param('_base_cisco.yaml', {'extends': ['_base.yaml', '_cisco-generic.yaml']}, id='generic'),
        pytest.param(
            '_base_cisco_voice.yaml',
            {'extends': ['_base.yaml', '_cisco-generic.yaml', '_cisco-voice.yaml']},
            id='voice',
        ),
    ],
)
def test_compat_cisco_base_profiles(definition_file, equivalent_definition):
    # type: (str, dict) -> None
    """
    Cisco and Cisco Voice base profiles were replaced by mixins (see Pull #6792).

    But their definition files should still be present and contain equivalent metrics to ensure backward compatibility.
    """
    definition = get_profile_definition({'definition_file': definition_file})

    recursively_expand_base_profiles(definition)
    recursively_expand_base_profiles(equivalent_definition)

    assert definition == equivalent_definition


@pytest.mark.usefixtures("dd_environment")
def test_cisco_voice(aggregator):
    run_profile_check('cisco_icm')

    tags = [
        'snmp_profile:cisco_icm',
        'snmp_host:test',
        'device_hostname:test',
        'device_vendor:cisco',
    ] + common.CHECK_TAGS

    resources = ["hrSWRunPerfMem", "hrSWRunPerfCPU"]

    common.assert_common_metrics(aggregator, tags)

    for resource in resources:
        aggregator.assert_metric('snmp.{}'.format(resource), metric_type=aggregator.GAUGE, tags=tags)

    run_indices = [4, 7, 8, 9, 10, 18, 24, 29, 30]
    for index in run_indices:
        status_tags = tags + ['run_index:{}'.format(index)]
        aggregator.assert_metric('snmp.hrSWRunStatus', metric_type=aggregator.GAUGE, tags=status_tags)

    cvp_gauges = [
        "ccvpSipIntAvgLatency1",
        "ccvpSipIntAvgLatency2",
        "ccvpSipIntConnectsRcv",
        "ccvpSipIntNewCalls",
        "ccvpSipRtActiveCalls",
        "ccvpSipRtTotalCallLegs",
        "ccvpLicRtPortsInUse",
        "ccvpLicAggMaxPortsInUse",
    ]

    for cvp in cvp_gauges:
        aggregator.assert_metric('snmp.{}'.format(cvp), metric_type=aggregator.GAUGE, tags=tags)

    ccms_counts = ["ccmRejectedPhones", "ccmUnregisteredPhones"]

    ccms_gauges = ["ccmRegisteredGateways", "ccmRegisteredPhones"]

    for ccm in ccms_counts:
        aggregator.assert_metric('snmp.{}'.format(ccm), metric_type=aggregator.RATE, tags=tags)

    for ccm in ccms_gauges:
        aggregator.assert_metric('snmp.{}'.format(ccm), metric_type=aggregator.GAUGE, tags=tags)

    calls = [
        "cvCallVolPeerIncomingCalls",
        "cvCallVolPeerOutgoingCalls",
    ]

    peers = [4, 13, 14, 17, 18, 22, 25, 30, 31]
    for call in calls:
        for peer in peers:
            peer_tags = tags + ["peer_index:{}".format(peer)]
            aggregator.assert_metric('snmp.{}'.format(call), metric_type=aggregator.GAUGE, tags=peer_tags)

    calls = [
        "cvCallVolMediaIncomingCalls",
        "cvCallVolMediaOutgoingCalls",
    ]

    for call in calls:
        aggregator.assert_metric('snmp.{}'.format(call), metric_type=aggregator.GAUGE, tags=tags)

    dial_controls = [
        "dialCtlPeerStatsAcceptCalls",
        "dialCtlPeerStatsFailCalls",
        "dialCtlPeerStatsRefuseCalls",
        "dialCtlPeerStatsSuccessCalls",
    ]

    for ctl in dial_controls:
        aggregator.assert_metric(
            'snmp.{}'.format(ctl), metric_type=aggregator.MONOTONIC_COUNT, tags=["peer_index:7"] + tags
        )

    pim_tags = tags + ['pim_host:test', 'pim_name:name', 'pim_num:2']
    aggregator.assert_metric('snmp.{}'.format("cccaPimStatus"), metric_type=aggregator.GAUGE, tags=pim_tags)
    aggregator.assert_metric('snmp.{}'.format("sysUpTimeInstance"), metric_type=aggregator.GAUGE, tags=tags, count=1)

    instance_numbers = ['4446', '5179', '12093', '19363', '25033', '37738', '42562', '51845', '62906', '63361']
    for metric in CCCA_ROUTER_GAUGES:
        for instance_number in instance_numbers:
            instance_tags = tags + ['instance_number:{}'.format(instance_number)]
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=instance_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_f5(aggregator):
    profile = 'f5-big-ip'
    run_profile_check(profile)

    gauges = [
        'sysStatMemoryTotal',
        'sysStatMemoryUsed',
        'sysGlobalTmmStatMemoryTotal',
        'sysGlobalTmmStatMemoryUsed',
        'sysGlobalHostOtherMemoryTotal',
        'sysGlobalHostOtherMemoryUsed',
        'sysGlobalHostSwapTotal',
        'sysGlobalHostSwapUsed',
        'sysTcpStatOpen',
        'sysTcpStatCloseWait',
        'sysTcpStatFinWait',
        'sysTcpStatTimeWait',
        'sysUdpStatOpen',
        'sysClientsslStatCurConns',
    ]
    counts = [
        'sysTcpStatAccepts',
        'sysTcpStatAcceptfails',
        'sysTcpStatConnects',
        'sysTcpStatConnfails',
        'sysUdpStatAccepts',
        'sysUdpStatAcceptfails',
        'sysUdpStatConnects',
        'sysUdpStatConnfails',
        'sysClientsslStatEncryptedBytesIn',
        'sysClientsslStatEncryptedBytesOut',
        'sysClientsslStatDecryptedBytesIn',
        'sysClientsslStatDecryptedBytesOut',
        'sysClientsslStatHandshakeFailures',
    ]
    cpu_rates = [
        'sysMultiHostCpuUser',
        'sysMultiHostCpuNice',
        'sysMultiHostCpuSystem',
        'sysMultiHostCpuIdle',
        'sysMultiHostCpuIrq',
        'sysMultiHostCpuSoftirq',
        'sysMultiHostCpuIowait',
    ]
    cpu_gauges = ['sysMultiHostCpuUsageRatio', 'cpu.usage']

    interfaces = [
        (32, 'mgmt', 'desc1'),
        (48, '1.0', 'desc2'),
        (80, '/Common/http-tunnel', 'desc3'),
        (96, '/Common/socks-tunnel', 'desc4'),
        (112, '/Common/internal', 'desc5'),
    ]
    interfaces_with_bandwidth_usage = {
        '1.0',
        'mgmt',
        '/Common/internal',
    }
    tags = [
        'snmp_profile:' + profile,
        'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
        'device_hostname:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
        'device_vendor:f5',
    ]
    tags += common.CHECK_TAGS

    common.assert_common_metrics(aggregator, tags)

    for metric in gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for metric in counts:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)
    for metric in cpu_rates:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=['cpu:0'] + tags, count=1)
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=['cpu:1'] + tags, count=1)
    for metric in cpu_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=['cpu:0'] + tags, count=1)
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=['cpu:1'] + tags, count=1)

    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for index, interface, desc in interfaces:
        interface_tags = [
            'interface:{}'.format(interface),
            'interface_alias:{}'.format(desc),
            'interface_index:{}'.format(index),
        ] + tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=interface_tags, count=1
            )
        for metric in IF_RATES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=interface_tags, count=1
            )
        if interface in interfaces_with_bandwidth_usage:
            for metric in IF_BANDWIDTH_USAGE:
                aggregator.assert_metric(
                    'snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=interface_tags, count=1
                )

        for metric in IF_GAUGES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.GAUGE,
                tags=interface_tags,
                count=1,
            )

    for version in ['ipv4', 'ipv6']:
        ip_tags = ['ipversion:{}'.format(version)] + tags
        for metric in IP_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=ip_tags, count=1
            )

    for metric in LTM_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    servers = ['server1', 'server2', 'server3']
    for server in servers:
        server_tags = tags + ['server:{}'.format(server)]
        for metric in LTM_VIRTUAL_SERVER_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=server_tags, count=1)
        for metric in LTM_VIRTUAL_SERVER_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=server_tags, count=1
            )
        for metric in LTM_VIRTUAL_SERVER_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=server_tags, count=1)

    nodes = ['node1', 'node2', 'node3']
    for node in nodes:
        node_tags = tags + ['node:{}'.format(node)]
        for metric in LTM_NODES_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=node_tags, count=1)
        for metric in LTM_NODES_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=node_tags, count=1
            )
        for metric in LTM_NODES_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=node_tags, count=1)

    pools = ['pool1', 'pool2']
    for pool in pools:
        pool_tags = tags + ['pool:{}'.format(pool)]
        for metric in LTM_POOL_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=pool_tags, count=1)
        for metric in LTM_POOL_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=pool_tags, count=1
            )
        for metric in LTM_POOL_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=pool_tags, count=1)

    pool_members = [('pool1', 'node1'), ('pool1', 'node2'), ('pool2', 'node3')]
    for pool, node in pool_members:
        pool_member_tags = tags + ['pool:{}'.format(pool), 'node:{}'.format(node)]
        for metric in LTM_POOL_MEMBER_GAUGES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=pool_member_tags, count=1
            )
        for metric in LTM_POOL_MEMBER_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=pool_member_tags, count=1
            )
        for metric in LTM_POOL_MEMBER_RATES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=pool_member_tags, count=1
            )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_device(aggregator):
    profile = "generic-device"
    run_profile_check(profile)
    common_tags = common.CHECK_TAGS + ['snmp_profile:' + profile]

    common.assert_common_metrics(aggregator, common_tags)

    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    interfaces = [
        (13, 'eth0', 'kept'),
        (15, 'eth1', 'their forward oxen'),
    ]
    for index, interface, if_desc in interfaces:
        tags = [
            'interface:{}'.format(interface),
            'interface_alias:{}'.format(if_desc),
            'interface_index:{}'.format(index),
        ] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in IF_BANDWIDTH_USAGE:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)
    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in IP_COUNTS + IPX_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IP_IF_COUNTS:
            for interface in ['17', '21']:
                tags = ['ipversion:{}'.format(version), 'interface:{}'.format(interface)] + common_tags
                aggregator.assert_metric(
                    'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
                )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_f5_router(aggregator):
    # Use the generic profile against the f5 device
    instance = common.generate_instance_config([])
    instance['community_string'] = 'f5-big-ip'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'router': {'definition_file': 'generic-device.yaml'}}}
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    interfaces = [
        (32, 'mgmt', 'desc1'),
        (48, '1.0', 'desc2'),
        (80, '/Common/http-tunnel', 'desc3'),
        (96, '/Common/socks-tunnel', 'desc4'),
        (112, '/Common/internal', 'desc5'),
    ]
    interfaces_with_bandwidth_usage = {
        '1.0',
        'mgmt',
        '/Common/internal',
    }
    common_tags = [
        'snmp_profile:router',
        'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
        'device_hostname:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
    ]
    common_tags.extend(common.CHECK_TAGS)

    common.assert_common_metrics(aggregator, common_tags)

    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for index, interface, desc in interfaces:
        tags = [
            'interface:{}'.format(interface),
            'interface_alias:{}'.format(desc),
            'interface_index:{}'.format(index),
        ] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        if interface in interfaces_with_bandwidth_usage:
            for metric in IF_BANDWIDTH_USAGE:
                aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in IP_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_cisco_3850(aggregator):
    profile = "cisco-3850"
    run_profile_check(profile)
    # We're not covering all interfaces
    interfaces = ["Gi1/0/{}".format(i) for i in range(1, 48)]
    common_tags = common.CHECK_TAGS + [
        'snmp_host:Cat-3850-4th-Floor.companyname.local',
        'device_hostname:Cat-3850-4th-Floor.companyname.local',
        'snmp_profile:' + profile,
        'device_vendor:cisco',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    indexes = {
        'Ca0': '127',
        'Ca1': '128',
        'Ca10': '138',
        'Ca11': '139',
        'Ca12': '140',
        'Ca13': '141',
        'Ca14': '142',
        'Ca2': '129',
        'Ca3': '130',
        'Ca4': '131',
        'Ca5': '132',
        'Ca6': '133',
        'Ca7': '134',
        'Ca8': '136',
        'Ca9': '137',
        'Gi0/0': '1',
        'Gi1/0/1': '3',
        'Gi1/0/10': '12',
        'Gi1/0/11': '13',
        'Gi1/0/12': '14',
        'Gi1/0/13': '15',
        'Gi1/0/14': '16',
        'Gi1/0/15': '17',
        'Gi1/0/16': '18',
        'Gi1/0/17': '19',
        'Gi1/0/18': '20',
        'Gi1/0/19': '21',
        'Gi1/0/2': '4',
        'Gi1/0/20': '22',
        'Gi1/0/21': '23',
        'Gi1/0/22': '24',
        'Gi1/0/23': '25',
        'Gi1/0/24': '26',
        'Gi1/0/25': '27',
        'Gi1/0/26': '28',
        'Gi1/0/27': '29',
        'Gi1/0/28': '30',
        'Gi1/0/29': '31',
        'Gi1/0/3': '5',
        'Gi1/0/30': '32',
        'Gi1/0/31': '33',
        'Gi1/0/32': '34',
        'Gi1/0/33': '35',
        'Gi1/0/34': '36',
        'Gi1/0/35': '37',
        'Gi1/0/36': '38',
        'Gi1/0/37': '39',
        'Gi1/0/38': '40',
        'Gi1/0/39': '41',
        'Gi1/0/4': '6',
        'Gi1/0/40': '42',
        'Gi1/0/41': '43',
        'Gi1/0/42': '44',
        'Gi1/0/43': '45',
        'Gi1/0/44': '46',
        'Gi1/0/45': '47',
        'Gi1/0/46': '48',
        'Gi1/0/47': '49',
        'Gi1/0/48': '50',
        'Gi1/0/5': '7',
        'Gi1/0/6': '8',
        'Gi1/0/7': '9',
        'Gi1/0/8': '10',
        'Gi1/0/9': '11',
        'Gi1/1/1': '51',
        'Gi1/1/2': '52',
        'Gi1/1/3': '53',
        'Gi1/1/4': '54',
        'Gi2/0/1': '63',
        'Gi2/0/10': '72',
        'Gi2/0/11': '73',
        'Gi2/0/12': '74',
        'Gi2/0/13': '75',
        'Gi2/0/14': '76',
        'Gi2/0/15': '77',
        'Gi2/0/16': '78',
        'Gi2/0/17': '79',
        'Gi2/0/18': '80',
        'Gi2/0/19': '81',
        'Gi2/0/2': '64',
        'Gi2/0/20': '82',
        'Gi2/0/21': '83',
        'Gi2/0/22': '84',
        'Gi2/0/23': '85',
        'Gi2/0/24': '86',
        'Gi2/0/25': '87',
        'Gi2/0/26': '88',
        'Gi2/0/27': '89',
        'Gi2/0/28': '90',
        'Gi2/0/29': '91',
        'Gi2/0/3': '65',
        'Gi2/0/30': '92',
        'Gi2/0/31': '93',
        'Gi2/0/32': '94',
        'Gi2/0/33': '95',
        'Gi2/0/34': '96',
        'Gi2/0/35': '97',
        'Gi2/0/36': '98',
        'Gi2/0/37': '99',
        'Gi2/0/38': '100',
        'Gi2/0/39': '101',
        'Gi2/0/4': '66',
        'Gi2/0/40': '102',
        'Gi2/0/41': '103',
        'Gi2/0/42': '104',
        'Gi2/0/43': '105',
        'Gi2/0/44': '106',
        'Gi2/0/45': '107',
        'Gi2/0/46': '108',
        'Gi2/0/47': '109',
        'Gi2/0/48': '110',
        'Gi2/0/5': '67',
        'Gi2/0/6': '68',
        'Gi2/0/7': '69',
        'Gi2/0/8': '70',
        'Gi2/0/9': '71',
        'Gi2/1/1': '111',
        'Gi2/1/2': '112',
        'Gi2/1/3': '113',
        'Gi2/1/4': '114',
        'Lo0': '122',
        'Nu0': '2',
        'Po15': '123',
        'StackPort1': '59',
        'StackPort2': '119',
        'Te1/1/1': '55',
        'Te1/1/2': '56',
        'Te1/1/3': '57',
        'Te1/1/4': '58',
        'Te2/1/1': '115',
        'Te2/1/2': '116',
        'Te2/1/3': '117',
        'Te2/1/4': '118',
        'Vl1': '62',
        'Vl164': '126',
        'Vl19': '135',
        'Vl195': '125',
        'Vl95': '124',
    }
    aliases = {
        'Gi1/0/24': 'LWAP-example',
        'Gi1/0/33': 'switchboard console',
        'Gi1/0/38': 'Mitel Console',
        'Gi1/1/3': 'Link to Switch',
        'Gi2/0/13': 'AP01',
        'Gi2/0/14': 'AP02',
        'Gi2/0/15': 'AP03',
        'Gi2/0/16': 'AP04',
        'Gi2/0/17': 'AP05',
        'Gi2/0/18': 'AP06',
        'Gi2/1/4': 'Link to Switch',
    }

    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for interface in interfaces:
        alias = aliases.get(interface, '')
        index = indexes.get(interface, '')
        tags = [
            'interface:{}'.format(interface),
            'interface_alias:{}'.format(alias),
            'interface_index:{}'.format(index),
        ] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in IF_BANDWIDTH_USAGE:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)

        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)

    for metric in IP_COUNTS + IPX_COUNTS:
        tags = common_tags + ['ipversion:ipv6']
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    sensors = [1006, 1007, 1008, 2006, 2007, 2008]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)
    frus = [1001, 1010, 2001, 2010]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in FRU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [1000, 2000]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in CPU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in CIE_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    power_supplies = [
        (1, 'Switch 1 - Power Supply B, NotExist'),
        (1, 'Switch 2 - Power Supply B, NotExist'),
        (2, 'Switch 1 - Power Supply A, Normal'),
        (2, 'Switch 2 - Power Supply A, Normal'),
    ]
    for source, descr in power_supplies:
        env_tags = ['power_source:{}'.format(source), 'power_status_descr:{}'.format(descr)]
        aggregator.assert_metric(
            'snmp.ciscoEnvMonSupplyState', metric_type=aggregator.GAUGE, tags=env_tags + common_tags
        )

    aggregator.assert_metric('snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_metric('snmp.cswStackPortOperStatus', metric_type=aggregator.GAUGE)

    for switch, mac_addr in [(1, '0x046c9d42b080'), (2, '0xdccec1430680')]:
        tags = ['entity_name:Switch {}'.format(switch), 'mac_addr:{}'.format(mac_addr)] + common_tags
        aggregator.assert_metric('snmp.cswSwitchState', metric_type=aggregator.GAUGE, tags=tags)

    frus = [1011, 1012, 1013, 2011, 2012, 2013]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        aggregator.assert_metric(
            'snmp.cefcFanTrayOperStatus', metric_type=aggregator.GAUGE, tags=['fru:{}'.format(fru)] + common_tags
        )

    for mem_metrics in MEMORY_METRICS:
        for pool in ['Processor', 'IOS Process stack']:
            tags = ['mem_pool_name:{}'.format(pool)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(mem_metrics), metric_type=aggregator.GAUGE, tags=tags)

    neighbor_metrics = [
        ('ospfNbrEvents', aggregator.RATE),
        ('ospfNbrState', aggregator.GAUGE),
        ('ospfNbrLsRetransQLen', aggregator.GAUGE),
    ]
    for metric, metric_type in neighbor_metrics:
        tags = ['neighbor_ip:192.29.116.26', 'neighbor_id:192.29.66.79', 'neighbor_state:8'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=metric_type, tags=tags, count=1)

    lls_metrics = ['ospfIfRetransInterval', 'ospfIfState']
    for metric in lls_metrics:
        tags = ['ospf_ip_addr:192.29.116.25', 'if_state:6'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for temp_index in [1006, 1007, 1008, 2006, 2007, 2008]:
        env_tag = ['temp_index:{}'.format(temp_index), 'temp_state:1']
        aggregator.assert_metric(
            'snmp.ciscoEnvMonTemperatureStatusValue', metric_type=aggregator.GAUGE, tags=env_tag + common_tags
        )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_meraki_cloud_controller(aggregator):
    run_profile_check('meraki-cloud-controller')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:meraki-cloud-controller',
        'snmp_host:dashboard.meraki.com',
        'device_hostname:dashboard.meraki.com',
        'device_vendor:meraki',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    dev_metrics = ['devStatus', 'devClientCount']
    dev_tags = [
        'device_name:Gymnasium',
        'product:MR16-HW',
        'network:L_NETWORK',
        'mac_address:0x02020066f57f',
    ] + common_tags
    for metric in dev_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=dev_tags, count=1)

    if_tags = ['interface:wifi0', 'index:4', 'mac_address:0x02020066f500'] + common_tags
    if_metrics = ['devInterfaceSentPkts', 'devInterfaceRecvPkts', 'devInterfaceSentBytes', 'devInterfaceRecvBytes']
    for metric in if_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    # IF-MIB
    if_tags = ['interface:eth0', 'interface_index:11'] + common_tags
    for metric in IF_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=if_tags, count=1
        )

    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in IF_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    for metric in IF_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=if_tags, count=1)

    for metric in IF_BANDWIDTH_USAGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=if_tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_idrac(aggregator):
    run_profile_check('idrac')

    interfaces = ['eth0', 'en1']
    common_tags = common.CHECK_TAGS + ['snmp_profile:idrac', 'device_vendor:dell']

    common.assert_common_metrics(aggregator, common_tags)

    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common_tags
        for count in ADAPTER_IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        for gauge in IDRAC_SYSTEM_STATUS_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('supply1', '13', 'forward their oxen acted acted'),
        ('supply2', '16', 'quaintly but acted'),
    ]
    for name, number, fqdd in tag_mappings:
        tags = [
            'supply_name:{}'.format(name),
            'enclosure_power_supply_number:{}'.format(number),
            'enclosure_power_supply_fqdd:{}'.format(fqdd),
        ] + common_tags
        aggregator.assert_metric('snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=tags, count=1)

    disks = ['disk1', 'disk2']
    for disk in disks:
        tags = ['disk_name:{}'.format(disk)] + common_tags
        for gauge in DISK_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('battery1', 'but but acted driving driving'),
        ('battery2', 'oxen acted Jaded quaintly kept forward quaintly forward Jaded'),
    ]

    for name, fqdd in tag_mappings:
        tags = [
            'battery_name:{}'.format(name),
            'battery_fqdd:{}'.format(fqdd),
        ] + common_tags
        aggregator.assert_metric('snmp.batteryState', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        (
            'controller1',
            '4',
            'quaintly kept acted acted but acted zombies quaintly forward',
            'quaintly zombies acted driving oxen',
        ),
        ('controller2', '21', 'acted', 'driving quaintly'),
    ]
    for name, number, pci_slot, fqdd in tag_mappings:
        tags = [
            'controller_name:{}'.format(name),
            'controller_number:{}'.format(number),
            'controller_pci_slot:{}'.format(pci_slot),
            'controller_fqdd:{}'.format(fqdd),
        ] + common_tags
        aggregator.assert_metric('snmp.controllerRollUpStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    devices = ['device1', 'device2']
    indexes = ['10', '20']
    for device, index in zip(devices, indexes):
        tags = ['device_descr_name:{}'.format(device), 'chassis_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.{}'.format("pCIDeviceStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1)

    slots = ['slot1', 'slot2']
    indexes = ['19', '21']
    for slot, index in zip(slots, indexes):
        tags = ['slot_name:{}'.format(slot), 'chassis_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.{}'.format("systemSlotStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('29', 'device2', '0x9e00e0291401'), ('3', 'device1', '0x9e00e0291401')]
    for index, device, mac in tag_mappings:
        tags = [
            'chassis_index:{}'.format(index),
            'device_fqdd:{}'.format(device),
            'mac_addr:{}'.format(mac),
        ] + common_tags
        aggregator.assert_metric(
            'snmp.{}'.format("networkDeviceStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1
        )

    tag_mappings = [('3', '26'), ('31', '19')]
    for chassis_index, bios_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'system_bios_index:{}'.format(bios_index),
        ] + common_tags
        aggregator.assert_metric('snmp.systemBIOSStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('9', '26', '28'), ('18', '26', '4')]
    for chassis_index, probe_type, probe_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'probe_type:{}'.format(probe_type),
            'amperage_probe_index:{}'.format(probe_index),
        ] + common_tags
        for gauge in PROBE_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('12', '6', '15'), ('22', '3', '19')]
    for chassis_index, probe_type, probe_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'probe_type:{}'.format(probe_type),
            'voltage_probe_index:{}'.format(probe_index),
        ] + common_tags
        for gauge in VOLTAGE_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('18', '23', 'Jaded oxen driving zombies acted oxen'),
        ('29', '21', 'kept zombies oxen kept driving forward oxen'),
    ]
    for chassis_index, intrusion_index, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'intrusion_index:{}'.format(intrusion_index),
            'intrusion_location_name:{}'.format(location_name),
        ] + common_tags
        aggregator.assert_metric('snmp.intrusionStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.intrusionReading', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('16', '26', 'zombies driving'),
        ('17', '15', 'zombies'),
    ]
    for chassis_index, power_supply_index, power_supply_fqdd in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'power_supply_index:{}'.format(power_supply_index),
            'power_supply_fqdd:{}'.format(power_supply_fqdd),
        ] + common_tags
        aggregator.assert_metric('snmp.powerSupplyOutputWatts', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric(
            'snmp.powerSupplyMaximumInputVoltage', metric_type=aggregator.GAUGE, tags=tags, count=1
        )
        aggregator.assert_metric(
            'snmp.powerSupplyCurrentInputVoltage', metric_type=aggregator.GAUGE, tags=tags, count=1
        )

    tag_mappings = [
        ('12', '14', 'zombies quaintly forward acted quaintly acted Jaded zombies'),
        ('22', '22', 'acted quaintly their Jaded oxen forward forward'),
    ]
    for chassis_index, power_usage_index, power_usage_entity_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'power_usage_index:{}'.format(power_usage_index),
            'power_usage_entity_name:{}'.format(power_usage_entity_name),
        ] + common_tags
        aggregator.assert_metric('snmp.powerUsageStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('20', '31', 'quaintly but oxen Jaded driving'),
        ('21', '13', 'kept kept their but quaintly kept quaintly driving'),
    ]
    for chassis_index, battery_index, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'system_battery_index:{}'.format(battery_index),
            'system_battery_location_name:{}'.format(location_name),
        ] + common_tags
        aggregator.assert_metric('snmp.systemBatteryStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.systemBatteryReading', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('1', '19', 'driving oxen forward'),
        ('6', '31', 'their Jaded quaintly but but their quaintly kept acted'),
    ]
    for chassis_index, cooling_unit_index, cooling_unit_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'cooling_unit_index:{}'.format(cooling_unit_index),
            'cooling_unit_name:{}'.format(cooling_unit_name),
        ] + common_tags
        aggregator.assert_metric('snmp.coolingUnitRedundancyStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.coolingUnitStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('8', '11', '9', 'acted', 'acted'),
        ('19', '3', '10', 'acted oxen but zombies driving acted Jaded', 'quaintly kept'),
    ]
    for chassis_index, device_name, device_type, location_name, cooling_device_fqdd in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'cooling_device_name:{}'.format(device_name),
            'cooling_device_type:{}'.format(device_type),
            'cooling_device_location_name:{}'.format(location_name),
            'cooling_device_fqdd:{}'.format(cooling_device_fqdd),
        ] + common_tags
        aggregator.assert_metric('snmp.coolingDeviceStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.coolingDeviceReading', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.coolingDeviceDiscreteReading', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('7', '28', '2', 'quaintly their but forward acted acted kept Jaded forward'),
        ('15', '28', '2', 'but driving quaintly kept Jaded'),
    ]
    for chassis_index, probe_index, probe_type, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'temperature_probe_index:{}'.format(probe_index),
            'temperature_probe_type:{}'.format(probe_type),
            'temperature_probe_location_name:{}'.format(location_name),
        ] + common_tags
        aggregator.assert_metric('snmp.temperatureProbeStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.temperatureProbeReading', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric(
            'snmp.temperatureProbeDiscreteReading', metric_type=aggregator.GAUGE, tags=tags, count=1
        )

    tag_mappings = [
        ('4', '24', 'but oxen forward', 'their forward oxen'),
        (
            '19',
            '1',
            'but driving oxen but driving oxen oxen oxen forward',
            'zombies quaintly Jaded but Jaded driving acted forward',
        ),
    ]
    for chassis_index, device_index, brand_name, device_fqdd in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'processor_device_index:{}'.format(device_index),
            'processor_device_brand_name:{}'.format(brand_name),
            'processor_device_fqdd:{}'.format(device_fqdd),
        ] + common_tags
        aggregator.assert_metric('snmp.processorDeviceStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.processorDeviceMaximumSpeed', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.processorDeviceCurrentSpeed', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.processorDeviceVoltage', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('3', '11', 'driving zombies oxen driving kept Jaded driving'),
        (
            '18',
            '21',
            'kept kept',
        ),
    ]
    for chassis_index, status_index, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'processor_device_status_index:{}'.format(status_index),
            'processor_device_status_location_name:{}'.format(location_name),
        ] + common_tags
        aggregator.assert_metric('snmp.processorDeviceStatusStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.processorDeviceStatusReading', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('2', '11', 'but kept Jaded'),
        (
            '8',
            '3',
            'quaintly quaintly oxen oxen kept kept their acted forward',
        ),
    ]
    for chassis_index, fru_index, fru_fqdd in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'fru_index:{}'.format(fru_index),
            'fru_fqdd:{}'.format(fru_fqdd),
        ] + common_tags
        aggregator.assert_metric('snmp.fruInformationStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('2', 'driving quaintly kept Jaded forward but forward kept', 'Jaded but Jaded their'),
        (
            '8',
            'zombies quaintly kept kept but quaintly forward quaintly oxen',
            'oxen acted their their forward but Jaded zombies oxen',
        ),
    ]
    for disk_number, disk_name, disk_fqdd in tag_mappings:
        tags = [
            'virtual_disk_number:{}'.format(disk_number),
            'virtual_disk_name:{}'.format(disk_name),
            'virtual_disk_fqdd:{}'.format(disk_fqdd),
        ] + common_tags
        aggregator.assert_metric('snmp.virtualDiskState', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.virtualDiskSizeInMB', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.virtualDiskComponentStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.virtualDiskT10PIStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('2', '27'),
        (
            '83',
            '86',
        ),
    ]
    for chassis_index, psu_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'drs_psu_index:{}'.format(psu_index),
        ] + common_tags
        aggregator.assert_metric('snmp.drsWattsReading', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.drsAmpsReading', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.drsKWhCumulative', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    indexes = ['29', '22']
    device_types = ['26', '4']
    device_indexes = ['4', '21']
    for index, device_type, device_index in zip(indexes, device_types, device_indexes):
        tags = [
            'chassis_index:{}'.format(index),
            'device_type:{}'.format(device_type),
            'device_index:{}'.format(device_index),
        ] + common_tags
        aggregator.assert_metric(
            'snmp.{}'.format("memoryDeviceStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1
        )

    for gauge in DRS_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_cisco_nexus(aggregator):
    profile = "cisco-nexus"
    run_profile_check(profile)

    indexes = {
        'GigabitEthernet1/0/1': '2',
        'GigabitEthernet1/0/2': '13',
        'GigabitEthernet1/0/3': '20',
        'GigabitEthernet1/0/4': '22',
        'GigabitEthernet1/0/5': '23',
        'GigabitEthernet1/0/6': '25',
        'GigabitEthernet1/0/7': '29',
        'GigabitEthernet1/0/8': '30',
    }
    interfaces = ["GigabitEthernet1/0/{}".format(i) for i in range(1, 9)]

    common_tags = common.CHECK_TAGS + [
        'snmp_host:Nexus-eu1.companyname.managed',
        'device_hostname:Nexus-eu1.companyname.managed',
        'snmp_profile:' + profile,
        'device_vendor:cisco',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    for interface in interfaces:
        tags = [
            'interface:{}'.format(interface),
            'interface_alias:',
            'interface_index:{}'.format(indexes.get(interface)),
        ] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in IF_BANDWIDTH_USAGE:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)

    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    sensors = [1, 9, 11, 12, 12, 14, 17, 26, 29, 31]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)

    frus = [6, 7, 15, 16, 19, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in FRU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [3173, 6692, 11571, 19529, 30674, 38253, 52063, 54474, 55946, 63960]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in CPU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for index, state in [(3, 3), (6, 6), (8, 6), (11, 6), (13, 3), (14, 6), (20, 6), (21, 4), (31, 5)]:
        aggregator.assert_metric(
            'snmp.ciscoEnvMonTemperatureStatusValue',
            metric_type=aggregator.GAUGE,
            tags=['temp_state:{}'.format(state), 'temp_index:{}'.format(index)] + common_tags,
        )

    power_supply_tags = ['power_source:1', 'power_status_descr:Jaded driving their their their'] + common_tags
    aggregator.assert_metric('snmp.ciscoEnvMonSupplyState', metric_type=aggregator.GAUGE, tags=power_supply_tags)

    fan_indices = [4, 6, 7, 16, 21, 22, 25, 27]
    for index in fan_indices:
        tags = ['fan_status_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_metric(
        'snmp.cswStackPortOperStatus',
        metric_type=aggregator.GAUGE,
        tags=common_tags + ['interface:GigabitEthernet1/0/1'],
    )

    tag_rows = [
        ['mac_addr:0xffffffffffff', 'entity_name:name1'],
        ['mac_addr:0xffffffffffff', 'entity_name:name2'],
        ['mac_addr:0xffffffffffff', 'entity_name:name3'],
        ['mac_addr:0xffffffffffff', 'entity_name:name4'],
        ['mac_addr:0xffffffffffff', 'entity_name:name5'],
        ['mac_addr:0xffffffffffff', 'entity_name:name6'],
        ['mac_addr:0xffffffffffff', 'entity_name:name7'],
        ['mac_addr:0xffffffffffff', 'entity_name:name8'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cswSwitchState', metric_type=aggregator.GAUGE, tags=tag_row + common_tags)

    frus = [2, 7, 8, 21, 26, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        aggregator.assert_metric(
            'snmp.cefcFanTrayOperStatus', metric_type=aggregator.GAUGE, tags=['fru:{}'.format(fru)] + common_tags
        )

    nexus_mem_metrics = ["memory.free", "memory.used"]
    for metric in nexus_mem_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags + ['mem:1'])

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_dell_poweredge(aggregator):
    run_profile_check('dell-poweredge')

    # Poweredge
    sys_mem_gauges = [
        'operatingSystemMemoryAvailablePhysicalSize',
        'operatingSystemMemoryTotalPageFileSize',
        'operatingSystemMemoryAvailablePageFileSize',
        'operatingSystemMemoryTotalVirtualSize',
        'operatingSystemMemoryAvailableVirtualSize',
    ]
    power_supply_gauges = [
        'powerSupplyStatus',
        'powerSupplyOutputWatts',
        'powerSupplyMaximumInputVoltage',
        'powerSupplyCurrentInputVoltage',
    ]

    temperature_probe_gauges = ['temperatureProbeStatus', 'temperatureProbeReading']

    processor_device_gauges = ['processorDeviceStatus', 'processorDeviceThreadCount']

    cache_device_gauges = ['cacheDeviceStatus', 'cacheDeviceMaximumSize', 'cacheDeviceCurrentSize']

    memory_device_gauges = ['memoryDeviceStatus', 'memoryDeviceFailureModes']

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:dell-poweredge',
        'device_vendor:dell',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    chassis_indexes = [29, 31]
    for chassis_index in chassis_indexes:
        tags = ['chassis_index:{}'.format(chassis_index)] + common_tags
        for metric in sys_mem_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [5, 17]
    for index in indexes:
        tags = ['chassis_index:4', 'index:{}'.format(index)] + common_tags
        for metric in power_supply_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    tag_mappings = [
        ('14', '8', '2', 'but their forward oxen oxen'),
        ('18', '13', '16', 'acted Jaded kept kept but quaintly quaintly zombies'),
        ('21', '13', '1', 'kept oxen oxen forward'),
        ('22', '4', '3', 'but but oxen zombies quaintly quaintly but Jaded'),
        ('23', '23', '3', 'kept driving driving Jaded zombies forward quaintly zombies but'),
        ('24', '10', '3', 'acted their kept forward forward'),
        ('25', '17', '1', 'oxen their their oxen'),
    ]
    for chassis_index, probe_index, probe_type, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'index:{}'.format(probe_index),
            'temperature_probe_type:{}'.format(probe_type),
            'temperature_probe_location_name:{}'.format(location_name),
        ] + common_tags
        for metric in temperature_probe_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [17, 28]
    for index in indexes:
        tags = ['chassis_index:5', 'index:{}'.format(index)] + common_tags
        for metric in processor_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [15, 27]
    for index in indexes:
        tags = ['chassis_index:11', 'index:{}'.format(index)] + common_tags
        for metric in cache_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    serial_numbers = ['forward zombies acted Jaded', 'kept oxen their their oxen oxen']
    for serial_number in serial_numbers:
        tags = ['serial_number_name:{}'.format(serial_number), 'chassis_index:1'] + common_tags
        for metric in memory_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    ip_addresses = ['66.97.1.103', '62.148.76.32', '45.3.243.155']
    for ip_address in ip_addresses:
        tags = ['ip_address:{}'.format(ip_address)] + common_tags
        aggregator.assert_metric('snmp.networkDeviceStatus', metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    # Intel Adapter
    interfaces = ['eth0', 'en1']
    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common_tags
        for count in ADAPTER_IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        for gauge in POWEREDGE_SYSTEM_STATUS_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('3', '17', 'zombies kept their quaintly but'),
        ('6', '19', 'zombies'),
    ]
    for chassis_index, battery_index, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'battery_index:{}'.format(battery_index),
            'battery_location_name:{}'.format(location_name),
        ] + common_tags
        aggregator.assert_metric('snmp.batteryStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.batteryReading', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('3', '26'), ('31', '19')]
    for chassis_index, bios_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'system_bios_index:{}'.format(bios_index),
        ] + common_tags
        aggregator.assert_metric('snmp.systemBIOSStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('9', '26', '28'), ('18', '26', '4')]
    for chassis_index, probe_type, probe_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'probe_type:{}'.format(probe_type),
            'amperage_probe_index:{}'.format(probe_index),
        ] + common_tags
        for gauge in PROBE_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('12', '6', '15'), ('22', '3', '19')]
    for chassis_index, probe_type, probe_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'probe_type:{}'.format(probe_type),
            'voltage_probe_index:{}'.format(probe_index),
        ] + common_tags
        for gauge in VOLTAGE_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('18', '23', 'Jaded oxen driving zombies acted oxen'),
        ('29', '21', 'kept zombies oxen kept driving forward oxen'),
    ]
    for chassis_index, intrusion_index, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'intrusion_index:{}'.format(intrusion_index),
            'intrusion_location_name:{}'.format(location_name),
        ] + common_tags
        aggregator.assert_metric('snmp.intrusionStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.intrusionReading', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('12', '14', 'zombies quaintly forward acted quaintly acted Jaded zombies'),
        ('22', '22', 'acted quaintly their Jaded oxen forward forward'),
    ]
    for chassis_index, power_usage_index, power_usage_entity_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'power_usage_index:{}'.format(power_usage_index),
            'power_usage_entity_name:{}'.format(power_usage_entity_name),
        ] + common_tags
        aggregator.assert_metric('snmp.powerUsageStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('1', '19', 'driving oxen forward'),
        ('6', '31', 'their Jaded quaintly but but their quaintly kept acted'),
    ]
    for chassis_index, cooling_unit_index, cooling_unit_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'cooling_unit_index:{}'.format(cooling_unit_index),
            'cooling_unit_name:{}'.format(cooling_unit_name),
        ] + common_tags
        aggregator.assert_metric('snmp.coolingUnitRedundancyStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.coolingUnitStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('8', '11', '9', 'acted'),
        ('19', '3', '10', 'acted oxen but zombies driving acted Jaded'),
    ]
    for chassis_index, device_name, device_type, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'cooling_device_name:{}'.format(device_name),
            'cooling_device_type:{}'.format(device_type),
            'cooling_device_location_name:{}'.format(location_name),
        ] + common_tags
        aggregator.assert_metric('snmp.coolingDeviceStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.coolingDeviceReading', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.coolingDeviceDiscreteReading', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('3', '11', 'driving zombies oxen driving kept Jaded driving'),
        (
            '18',
            '21',
            'kept kept',
        ),
    ]
    for chassis_index, status_index, location_name in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'processor_device_status_index:{}'.format(status_index),
            'processor_device_status_location_name:{}'.format(location_name),
        ] + common_tags
        aggregator.assert_metric('snmp.processorDeviceStatusStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.processorDeviceStatusReading', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('2', '11'),
        (
            '8',
            '3',
        ),
    ]
    for chassis_index, fru_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'fru_index:{}'.format(fru_index),
        ] + common_tags
        aggregator.assert_metric('snmp.fruInformationStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [
        ('2', '11'),
        (
            '8',
            '3',
        ),
    ]
    for chassis_index, fru_index in tag_mappings:
        tags = [
            'chassis_index:{}'.format(chassis_index),
            'fru_index:{}'.format(fru_index),
        ] + common_tags
        aggregator.assert_metric('snmp.fruInformationStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('19', 'their kept kept zombies kept zombies their'), ('21', 'zombies their')]
    for index, slot in tag_mappings:
        tags = ['slot_name:{}'.format(slot), 'chassis_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.systemSlotStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('2', 'driving oxen oxen but'), ('7', 'kept but Jaded oxen quaintly Jaded zombies')]
    for index, descr_name in tag_mappings:
        tags = ['device_descr_name:{}'.format(descr_name), 'chassis_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.pCIDeviceStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_hp_ilo4(aggregator):
    profile = "hp-ilo4"
    run_profile_check(profile)

    status_gauges = [
        'cpqHeCritLogCondition',
        'cpqHeCorrMemLogStatus',
        'cpqHeCorrMemLogCondition',
        'cpqHeAsrStatus',
        'cpqHeAsrPost',
        'cpqHeAsrCondition',
        'cpqHeAsrNetworkAccessStatus',
        'cpqHeThermalCondition',
        'cpqHeThermalTempStatus',
        'cpqHeThermalSystemFanStatus',
        'cpqHeThermalCpuFanStatus',
        'cpqNicVtVirusActivity',
        'cpqSm2CntlrBatteryStatus',
        'cpqSm2CntlrRemoteSessionStatus',
        'cpqSm2CntlrInterfaceStatus',
    ]

    cpqhlth_counts = ['cpqHeAsrRebootCount', 'cpqHeCorrMemTotalErrs']

    cpqhlth_gauges = ['cpqHeSysUtilEisaBusMin', 'cpqHePowerMeterCurrReading', 'cpqHeSysUtilLifeTime']

    cpqsm2_gauges = [
        'cpqSm2CntlrBatteryPercentCharged',
        'cpqSm2CntlrSelfTestErrors',
        'cpqSm2EventTotalEntries',
    ]

    EMBEDDED = 2
    PCMCIA = 3
    card_locations = [EMBEDDED, PCMCIA]
    network_card_counts = [
        'cpqSm2NicXmitBytes',
        'cpqSm2NicXmitTotalPackets',
        'cpqSm2NicXmitDiscardPackets',
        'cpqSm2NicXmitErrorPackets',
        'cpqSm2NicXmitQueueLength',
        'cpqSm2NicRecvBytes',
        'cpqSm2NicRecvTotalPackets',
        'cpqSm2NicRecvDiscardPackets',
        'cpqSm2NicRecvErrorPackets',
        'cpqSm2NicRecvUnknownPackets',
    ]

    interfaces = ['eth0', 'en1']
    phys_adapter_counts = [
        'cpqNicIfPhysAdapterGoodTransmits',
        'cpqNicIfPhysAdapterGoodReceives',
        'cpqNicIfPhysAdapterBadTransmits',
        'cpqNicIfPhysAdapterBadReceives',
        'cpqNicIfPhysAdapterInOctets',
        'cpqNicIfPhysAdapterOutOctets',
    ]
    phys_adapter_gauges = ['cpqNicIfPhysAdapterSpeed', 'cpqNicIfPhysAdapterSpeedMbps']

    temperature_sensors = [1, 13, 28]
    batteries = [1, 3, 4, 5]

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:' + profile,
        'device_vendor:hp',
        'snmp_host:hp-ilo4.example',
        'device_hostname:hp-ilo4.example',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    for metric in status_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_metric('snmp.cpqSm2CntlrServerPowerState', metric_type=aggregator.GAUGE, tags=common_tags)

    for metric in cpqhlth_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in cpqhlth_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in cpqsm2_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for index in temperature_sensors:
        tags = ['temperature_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.cpqHeTemperatureCelsius', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cpqHeTemperatureCondition', metric_type=aggregator.GAUGE, tags=tags, count=1)

    for index in batteries:
        tags = ['battery_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.cpqHeSysBatteryCondition', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cpqHeSysBatteryStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    for location in card_locations:
        tags = ['nic_stats_location:{}'.format(location)] + common_tags
        for metric in network_card_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in phys_adapter_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in phys_adapter_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    drive_counts = [
        "cpqDaPhyDrvUsedReallocs",
        "cpqDaPhyDrvRefHours",
        "cpqDaPhyDrvHardReadErrs",
        "cpqDaPhyDrvRecvReadErrs",
        "cpqDaPhyDrvHardWriteErrs",
        "cpqDaPhyDrvRecvWriteErrs",
        "cpqDaPhyDrvHSeekErrs",
        "cpqDaPhyDrvSeekErrs",
    ]
    drive_gauges = [
        "cpqDaPhyDrvStatus",
        "cpqDaPhyDrvFactReallocs",
        "cpqDaPhyDrvSpinupTime",
        "cpqDaPhyDrvSize",
        "cpqDaPhyDrvSmartStatus",
        "cpqDaPhyDrvCurrentTemperature",
    ]
    drive_idx = [(0, 2), (0, 28), (8, 31), (9, 24), (9, 28), (10, 17), (11, 4), (12, 20), (18, 22), (23, 2)]
    for drive_cntrl_idx, drive_index in drive_idx:
        tags = ['drive_cntrl_idx:{}'.format(drive_cntrl_idx), "drive_index:{}".format(drive_index)] + common_tags
        for metric in drive_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in drive_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_proliant(aggregator):
    run_profile_check('hpe-proliant')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:hpe-proliant',
        'device_vendor:hp',
        'snmp_host:hpe-proliant.example',
        'device_hostname:hpe-proliant.example',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    cpu_gauges = [
        "cpqSeCpuSlot",
        "cpqSeCpuSpeed",
        "cpqSeCpuStatus",
        "cpqSeCpuExtSpeed",
        "cpqSeCpuCore",
        "cpqSeCPUCoreMaxThreads",
        "cpqSeCpuPrimary",
    ]
    cpu_indexes = [0, 4, 6, 8, 13, 15, 26, 27]
    for idx in cpu_indexes:
        tags = ['cpu_index:{}'.format(idx)] + common_tags
        for metric in cpu_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpu_util_gauges = ["cpqHoCpuUtilMin", "cpqHoCpuUtilFiveMin", "cpqHoCpuUtilThirtyMin", "cpqHoCpuUtilHour"]
    cpu_unit_idx = [4, 7, 13, 20, 22, 23, 29]
    for idx in cpu_unit_idx:
        tags = ['cpu_unit_index:{}'.format(idx)] + common_tags
        for metric in cpu_util_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    file_sys_gauges = [
        "cpqHoFileSysSpaceTotal",
        "cpqHoFileSysSpaceUsed",
        "cpqHoFileSysPercentSpaceUsed",
        "cpqHoFileSysAllocUnitsTotal",
        "cpqHoFileSysAllocUnitsUsed",
        "cpqHoFileSysStatus",
    ]
    file_sys_idx = [5, 8, 11, 15, 19, 21, 28, 30]
    for idx in file_sys_idx:
        tags = ['file_sys_index:{}'.format(idx)] + common_tags
        for metric in file_sys_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    memory_gauges = [
        "cpqSiMemModuleSize",
        "cpqSiMemModuleType",
        "cpqSiMemModuleSpeed",
        "cpqSiMemModuleTechnology",
        "cpqSiMemModuleECCStatus",
        "cpqSiMemModuleFrequency",
        "cpqSiMemModuleCellStatus",
    ]
    memory_idx = [(6, 16), (7, 17), (7, 30), (8, 20), (10, 4), (15, 27), (20, 14), (21, 14), (23, 0), (28, 20)]
    for board_idx, mem_module_index in memory_idx:
        tags = ['mem_board_index:{}'.format(board_idx), "mem_module_index:{}".format(mem_module_index)] + common_tags
        for metric in memory_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    drive_counts = [
        "cpqDaPhyDrvUsedReallocs",
        "cpqDaPhyDrvRefHours",
        "cpqDaPhyDrvHardReadErrs",
        "cpqDaPhyDrvRecvReadErrs",
        "cpqDaPhyDrvHardWriteErrs",
        "cpqDaPhyDrvRecvWriteErrs",
        "cpqDaPhyDrvHSeekErrs",
        "cpqDaPhyDrvSeekErrs",
    ]
    drive_gauges = [
        "cpqDaPhyDrvStatus",
        "cpqDaPhyDrvFactReallocs",
        "cpqDaPhyDrvSpinupTime",
        "cpqDaPhyDrvSize",
        "cpqDaPhyDrvSmartStatus",
        "cpqDaPhyDrvCurrentTemperature",
    ]
    drive_idx = [(0, 2), (0, 28), (8, 31), (9, 24), (9, 28), (10, 17), (11, 4), (12, 20), (18, 22), (23, 2)]
    for drive_cntrl_idx, drive_index in drive_idx:
        tags = ['drive_cntrl_idx:{}'.format(drive_cntrl_idx), "drive_index:{}".format(drive_index)] + common_tags
        for metric in drive_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in drive_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    interfaces = [
        (3, 'eth0', 'quaintly zombies quaintly forward'),
        (4, 'eth1', 'quaintly but quaintly quaintly'),
    ]

    for index, interface, desc in interfaces:
        if_tags = [
            'interface:{}'.format(interface),
            'interface_alias:{}'.format(desc),
            'interface_index:{}'.format(index),
        ] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=if_tags, count=1
            )

        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=if_tags, count=1)
        for metric in IF_BANDWIDTH_USAGE:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=if_tags, count=1)

    mem_boards = ['11', '12']
    for board in mem_boards:
        tags = ['mem_board_index:{}'.format(board)] + common_tags
        aggregator.assert_metric('snmp.cpqHeResMem2ModuleCondition', metric_type=aggregator.GAUGE, tags=tags, count=1)

    adapter_gauges = ['cpqNicIfPhysAdapterStatus', 'cpqNicIfPhysAdapterState']

    for gauge in adapter_gauges:
        tags = ['adapter_name:adapter', 'adapter_mac_addr:mac'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    power_metrics = [
        'cpqHeFltTolPowerSupplyStatus',
    ]
    for gauge in power_metrics:
        tags = ['chassis_num:30'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    controller_index = ['controller_index:3'] + common_tags
    aggregator.assert_metric(
        'snmp.{}'.format("cpqDaCntlrCondition"), metric_type=aggregator.GAUGE, tags=controller_index, count=1
    )

    tags = ['chassis_num:30', 'power_supply_status:3'] + common_tags
    aggregator.assert_metric(
        'snmp.{}'.format("cpqHeFltTolPowerSupplyCapacityUsed"),
        metric_type=aggregator.GAUGE,
        tags=tags,
        count=1,
    )
    aggregator.assert_metric(
        'snmp.{}'.format("cpqHeFltTolPowerSupplyCapacityMaximum"),
        metric_type=aggregator.GAUGE,
        tags=tags,
        count=1,
    )

    thermal_metrics = ['cpqHeThermalCondition', 'cpqHeSysUtilLifeTime', 'cpqHeFltTolPwrSupplyStatus']

    for metric in thermal_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_generic_host_resources(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = 'generic_host'
    instance['enforce_mib_constraints'] = False
    instance['profile'] = 'generic'

    init_config = {'profiles': {'generic': {'definition_file': '_generic-host-resources.yaml'}}}
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    common_tags = common.CHECK_TAGS + ['snmp_profile:generic']

    common.assert_common_metrics(aggregator, common_tags)

    sys_metrics = [
        'snmp.hrSystemUptime',
        'snmp.hrSystemNumUsers',
        'snmp.hrSystemProcesses',
        'snmp.hrSystemMaxProcesses',
    ]
    for metric in sys_metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    storages = [
        ('1.3.6.1.2.1.25.2.1.3', 'oxen their driving forward quaintly'),
        ('1.3.6.1.2.1.25.2.1.4', 'quaintly driving Jaded forward their quaintly zombies'),
    ]
    for storage_type, storage_desc in storages:
        tags = common_tags + ['storagetype:{}'.format(storage_type), 'storagedesc:{}'.format(storage_desc)]
        aggregator.assert_metric('snmp.hrStorageAllocationUnits', count=1, tags=tags)
        aggregator.assert_metric('snmp.hrStorageSize', count=1, tags=tags)
        aggregator.assert_metric('snmp.hrStorageUsed', count=1, tags=tags)
        aggregator.assert_metric('snmp.hrStorageAllocationFailures', count=1, tags=tags)

    processors = [
        ('1.3.6.1.3.81.16', '5'),
        ('1.3.6.1.3.95.73.140.186.121.144.199', '10'),
    ]
    for proc, hr_device_index in processors:
        tags = common_tags + ['processorid:{}'.format(proc), 'hr_device_index:{}'.format(hr_device_index)]
        aggregator.assert_metric('snmp.hrProcessorLoad', count=1, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_palo_alto(aggregator):
    profile = "palo-alto"
    run_profile_check(profile)

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:' + profile,
        'device_vendor:paloaltonetworks',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    session = [
        'panSessionUtilization',
        'panSessionMax',
        'panSessionActive',
        'panSessionActiveTcp',
        'panSessionActiveUdp',
        'panSessionActiveICMP',
        'panSessionActiveSslProxy',
        'panSessionSslProxyUtilization',
    ]

    global_protect = [
        'panGPGWUtilizationPct',
        'panGPGWUtilizationMaxTunnels',
        'panGPGWUtilizationActiveTunnels',
    ]

    entity = [
        'panEntityTotalPowerAvail',
        'panEntityTotalPowerUsed',
    ]

    entry = ['panEntryFRUModulePowerUsed', 'panEntryFRUModuleNumPorts']

    for metric in session:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in global_protect:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in entity:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in entry:
        # Needs cross table entPhysicalIsFRU tag
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)
    # Needs cross table entLogicalDescr tag
    aggregator.assert_metric('snmp.panEntryFanTrayPowerUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_cisco_asa_all(aggregator):
    profile = "cisco-asa"
    assert_cisco_asa(aggregator, profile)


@pytest.mark.usefixtures("dd_environment")
def test_cisco_asa_5525(aggregator):
    profile = "cisco-asa-5525"
    assert_cisco_asa(aggregator, profile)


def assert_cisco_asa(aggregator, profile):
    run_profile_check(profile)

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:' + profile,
        'snmp_host:kept',
        'device_hostname:kept',
        'device_vendor:cisco',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    if_tags = ['interface:eth0', 'interface_index:11'] + common_tags
    for metric in IF_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=if_tags, count=1
        )

    for metric in IF_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    for metric in IF_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=if_tags, count=1)

    for metric in IF_BANDWIDTH_USAGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=if_tags, count=1)

    aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1)

    frus = [3, 4, 5, 7, 16, 17, 24, 25]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in FRU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [7746]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in CPU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    sensor_tags = ['sensor_id:31', 'sensor_type:9'] + common_tags
    aggregator.assert_metric('snmp.entPhySensorValue', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)

    stat_tags = [(20, 2), (5, 5)]
    for svc, stat in stat_tags:
        aggregator.assert_metric(
            'snmp.cfwConnectionStatValue',
            metric_type=aggregator.GAUGE,
            tags=['stat_type:{}'.format(stat), 'service_type:{}'.format(svc)] + common_tags,
        )

    aggregator.assert_metric('snmp.crasNumDeclinedSessions', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.crasNumSessions', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.crasNumUsers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.crasNumSetupFailInsufResources', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags
    )
    aggregator.assert_metric('snmp.cipSecGlobalActiveTunnels', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cipSecGlobalHcInOctets', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.cipSecGlobalHcOutOctets', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)

    for index, state in [(3, 3), (6, 6), (8, 6), (11, 6), (13, 3), (14, 6), (20, 6), (21, 4), (31, 5)]:
        aggregator.assert_metric(
            'snmp.ciscoEnvMonTemperatureStatusValue',
            metric_type=aggregator.GAUGE,
            tags=['temp_state:{}'.format(state), 'temp_index:{}'.format(index)] + common_tags,
        )

    power_supply_tags = ['power_source:1', 'power_status_descr:Jaded driving their their their'] + common_tags
    aggregator.assert_metric('snmp.ciscoEnvMonSupplyState', metric_type=aggregator.GAUGE, tags=power_supply_tags)

    fan_indices = [4, 6, 7, 16, 21, 22, 25, 27]
    for index in fan_indices:
        tags = ['fan_status_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_metric('snmp.cswStackPortOperStatus', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(
        'snmp.cswSwitchState', metric_type=aggregator.GAUGE, tags=['mac_addr:0xffffffffffff'] + common_tags
    )

    frus = [2, 7, 8, 21, 26, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        aggregator.assert_metric(
            'snmp.cefcFanTrayOperStatus', metric_type=aggregator.GAUGE, tags=['fru:{}'.format(fru)] + common_tags
        )

    for mem_metrics in MEMORY_METRICS:
        tags = ['mem_pool_name:test_pool'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(mem_metrics), metric_type=aggregator.GAUGE, tags=tags)

    for conn in [1, 2, 5]:
        conn_tags = ['connection_type:{}'.format(conn)] + common_tags
        aggregator.assert_metric('snmp.cfwConnectionStatCount', metric_type=aggregator.RATE, tags=conn_tags)

    hardware_tags = [(3, 'Secondary unit'), (5, 'Primary unit'), (6, 'Failover LAN Interface')]
    for htype, hdesc in hardware_tags:
        aggregator.assert_metric(
            'snmp.cfwHardwareStatusValue',
            metric_type=aggregator.GAUGE,
            tags=['hardware_type:{}'.format(htype), 'hardware_desc:{}'.format(hdesc)] + common_tags,
        )

    for switch in [4684, 4850, 8851, 9997, 15228, 16580, 24389, 30813, 36264]:
        aggregator.assert_metric(
            'snmp.cvsChassisUpTime',
            metric_type=aggregator.GAUGE,
            tags=['chassis_switch_id:{}'.format(switch)] + common_tags,
        )
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)

    # RTT
    rtt_indexes = [1, 7, 10, 13, 15, 18, 20]
    rtt_types = [22, 21, 17, 6, 20, 8, 16]
    rtt_states = [3, 1, 6, 4, 6, 1, 6]
    rtt_gauges = ['rttMonLatestRttOperCompletionTime', 'rttMonLatestRttOperSense', 'rttMonCtrlOperTimeoutOccurred']
    for i in range(len(rtt_indexes)):
        tags = [
            "rtt_index:{}".format(rtt_indexes[i]),
            "rtt_type:{}".format(rtt_types[i]),
            "rtt_state:{}".format(rtt_states[i]),
        ] + common_tags
        for rtt in rtt_gauges:
            aggregator.assert_metric('snmp.{}'.format(rtt), metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_cisco_csr(aggregator):
    run_profile_check('cisco-csr1000v')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:cisco-csr1000v',
        'device_vendor:cisco',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    _check_bgp4(aggregator, common_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_checkpoint(aggregator):
    run_profile_check('checkpoint')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:checkpoint',
        'device_vendor:checkpoint',
        'snmp_host:checkpoint.device.name',
        'device_hostname:checkpoint.device.name',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.ipSystemStatsHCInReceives', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags + ['ipversion:ipv4']
    )
    aggregator.assert_metric('snmp.tcpActiveOpens', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.udpHCInDatagrams', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)

    cpu_metrics = [
        'multiProcUserTime',
        'multiProcSystemTime',
        'multiProcIdleTime',
        'multiProcUsage',
    ]
    cpu_cores = [7097, 13039, 13761, 28994, 29751, 33826, 40053, 48847, 61593, 65044]
    for core in cpu_cores:
        tags = ['cpu_core:{}'.format(core)] + common_tags
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_metric('snmp.procNum', metric_type=aggregator.GAUGE, tags=common_tags)

    mem_metrics = ['memTotalReal64', 'memActiveReal64', 'memFreeReal64', 'memTotalVirtual64', 'memActiveVirtual64']
    for metric in mem_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    disk_metrics = [
        'multiDiskSize',
        'multiDiskUsed',
        'multiDiskFreeTotalBytes',
        'multiDiskFreeAvailableBytes',
        'multiDiskFreeTotalPercent',
        'multiDiskFreeAvailablePercent',
    ]
    appliance_metrics = [
        'fanSpeedSensorValue',
        'fanSpeedSensorStatus',
        'tempertureSensorValue',
        'tempertureSensorStatus',
    ]
    common_indices = range(10)
    common_names = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth']
    for idx in common_indices:
        name = common_names[idx]
        tags = ['disk_index:{}'.format(idx), 'disk_name:{}'.format(name)] + common_tags
        for metric in disk_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

        tags = ['sensor_index:{}'.format(idx), 'sensor_name:{}'.format(name)] + common_tags
        for metric in appliance_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    fw_count_metrics = ['fwAccepted', 'fwDropped', 'fwRejected']
    for metric in fw_count_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)

    fw_gauge_metrics = ['fwNumConn', 'fwPeakNumConn']
    for metric in fw_gauge_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_checkpoint_firewall(aggregator):
    run_profile_check(recording_name='checkpoint', profile_name='checkpoint-firewall')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:checkpoint-firewall',
        'device_vendor:checkpoint',
        'snmp_host:checkpoint.device.name',
        'device_hostname:checkpoint.device.name',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.ipSystemStatsHCInReceives', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags + ['ipversion:ipv4']
    )
    aggregator.assert_metric('snmp.tcpActiveOpens', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.udpHCInDatagrams', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)

    cpu_metrics = [
        'multiProcUserTime',
        'multiProcSystemTime',
        'multiProcIdleTime',
        'multiProcUsage',
    ]
    cpu_cores = [7097, 13039, 13761, 28994, 29751, 33826, 40053, 48847, 61593, 65044]
    for core in cpu_cores:
        tags = ['cpu_core:{}'.format(core)] + common_tags
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_metric('snmp.procNum', metric_type=aggregator.GAUGE, tags=common_tags)

    mem_metrics = ['memTotalReal64', 'memActiveReal64', 'memFreeReal64', 'memTotalVirtual64', 'memActiveVirtual64']
    for metric in mem_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    disk_metrics = [
        'multiDiskSize',
        'multiDiskUsed',
        'multiDiskFreeTotalBytes',
        'multiDiskFreeAvailableBytes',
        'multiDiskFreeTotalPercent',
        'multiDiskFreeAvailablePercent',
    ]
    appliance_metrics = [
        'fanSpeedSensorValue',
        'fanSpeedSensorStatus',
        'tempertureSensorValue',
        'tempertureSensorStatus',
    ]
    common_indices = range(10)
    common_names = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth']
    for idx in common_indices:
        name = common_names[idx]
        tags = ['disk_index:{}'.format(idx), 'disk_name:{}'.format(name)] + common_tags
        for metric in disk_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

        tags = ['sensor_index:{}'.format(idx), 'sensor_name:{}'.format(name)] + common_tags
        for metric in appliance_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    fw_count_metrics = ['fwAccepted', 'fwDropped', 'fwRejected']
    for metric in fw_count_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)

    fw_gauge_metrics = ['fwNumConn', 'fwPeakNumConn']
    for metric in fw_gauge_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_arista(aggregator):
    run_profile_check('arista')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:arista',
        'device_vendor:arista',
        'snmp_host:DCS-7504-name',
        'device_hostname:DCS-7504-name',
    ]

    common.assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric(
        'snmp.aristaEgressQueuePktsDropped',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=common_tags + ['interface_index:13', 'queue_index:10'],
        count=1,
    )
    aggregator.assert_metric(
        'snmp.aristaEgressQueuePktsDropped',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=common_tags + ['interface_index:28', 'queue_index:22'],
        count=1,
    )
    aggregator.assert_metric(
        'snmp.aristaIngressQueuePktsDropped',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=common_tags + ['interface_index:7', 'queue_index:25'],
        count=1,
    )
    aggregator.assert_metric(
        'snmp.aristaIngressQueuePktsDropped',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=common_tags + ['interface_index:8', 'queue_index:24'],
        count=1,
    )

    for sensor_id, sensor_type in [(1, 11), (7, 8)]:
        sensor_tags = ['sensor_id:{}'.format(sensor_id), 'sensor_type:{}'.format(sensor_type)] + common_tags
        aggregator.assert_metric('snmp.entPhySensorValue', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)
        aggregator.assert_metric('snmp.entPhySensorOperStatus', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_aruba(aggregator):
    run_profile_check('aruba')

    common_tags = common.CHECK_TAGS + ['snmp_profile:aruba-switch', 'device_vendor:aruba']

    common.assert_common_metrics(aggregator, common_tags)

    for fan in [18, 28]:
        fan_tags = common_tags + ['fan_index:{}'.format(fan)]
        aggregator.assert_metric('snmp.sysExtFanStatus', metric_type=aggregator.GAUGE, tags=fan_tags, count=1)
    for psu in [1, 17]:
        psu_tags = common_tags + ['powersupply_index:{}'.format(psu)]
        aggregator.assert_metric('snmp.sysExtPowerSupplyStatus', metric_type=aggregator.GAUGE, tags=psu_tags, count=1)
    for proc in [11, 26]:
        proc_tags = common_tags + ['processor_index:{}'.format(proc)]
        aggregator.assert_metric('snmp.sysExtProcessorLoad', metric_type=aggregator.GAUGE, tags=proc_tags, count=1)
    for mem in [3, 20]:
        mem_tags = common_tags + ['memory_index:{}'.format(mem)]
        aggregator.assert_metric('snmp.sysExtMemorySize', metric_type=aggregator.GAUGE, tags=mem_tags, count=1)
        aggregator.assert_metric('snmp.sysExtMemoryUsed', metric_type=aggregator.GAUGE, tags=mem_tags, count=1)
        aggregator.assert_metric('snmp.sysExtMemoryFree', metric_type=aggregator.GAUGE, tags=mem_tags, count=1)

    aggregator.assert_metric(
        'snmp.wlsxSysExtPacketLossPercent', metric_type=aggregator.GAUGE, tags=common_tags, count=1
    )

    # OSPF metrics
    neighbor_metrics = [
        ('ospfNbrEvents', aggregator.RATE),
        ('ospfNbrState', aggregator.GAUGE),
        ('ospfNbrLsRetransQLen', aggregator.GAUGE),
    ]
    for metric, metric_type in neighbor_metrics:
        tags = ['neighbor_ip:192.29.116.26', 'neighbor_id:192.29.66.79', 'neighbor_state:8'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=metric_type, tags=tags, count=1)

    virtual_neighbor_metrics = [
        ('ospfVirtNbrState', aggregator.GAUGE),
        ('ospfVirtNbrEvents', aggregator.RATE),
        ('ospfVirtNbrLsRetransQLen', aggregator.GAUGE),
    ]
    for metric, metric_type in virtual_neighbor_metrics:
        for ip, nbr in [('74.210.82.1', '194.154.66.112'), ('122.226.86.1', '184.201.101.140')]:
            tags = ['neighbor_ip:{}'.format(ip), 'neighbor_id:{}'.format(nbr), 'neighbor_state:6'] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=metric_type, tags=tags, count=1)

    lls_metrics = ['ospfIfRetransInterval', 'ospfIfState', 'ospfIfLsaCount']
    for metric in lls_metrics:
        for ip, nbr, state in [('58.115.169.188', '192.29.66.79', 2), ('18.2.8.29', '118.246.193.247', 4)]:
            tags = [
                'ospf_ip_addr:{}'.format(ip),
                'neighbor_id:{}'.format(nbr),
                'if_state:{}'.format(state),
            ] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    virtual_lls_metrics = ['ospfVirtIfRetransInterval', 'ospfVirtIfState', 'ospfVirtIfLsaCount']
    for metric in virtual_lls_metrics:
        for nbr, state in [('194.154.66.112', 4), ('184.201.101.140', 1)]:
            tags = ['neighbor_id:{}'.format(nbr), 'if_state:{}'.format(state)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_chatsworth(aggregator):
    profile = "chatsworth_pdu"
    host = "chatsworth_pdu.device.name"
    run_profile_check(profile)

    # Legacy global tags are applied to all metrics
    legacy_global_tags = [
        'legacy_pdu_macaddress:00:0E:D3:AA:CC:EE',
        'legacy_pdu_model:P10-1234-ABC',
        'legacy_pdu_name:legacy-name1',
        'legacy_pdu_version:1.3.6.1.4.1.30932.1.1',
    ]
    common_tags = (
        common.CHECK_TAGS
        + legacy_global_tags
        + ['snmp_profile:' + profile, 'device_vendor:chatsworth', 'snmp_host:' + host, 'device_hostname:' + host]
    )

    common.assert_common_metrics(aggregator, common_tags)

    # Legacy metrics
    legacy_pdu_tags = common_tags
    legacy_pdu_gauge_metrics = [
        'snmp.pduRole',
        'snmp.outOfService',
    ]
    legacy_pdu_monotonic_count_metrics = []
    for line in range(1, 4):
        legacy_pdu_gauge_metrics.append('snmp.line{}curr'.format(line))
    for branch in range(1, 3):
        legacy_pdu_gauge_metrics.append('snmp.temperatureProbe{}'.format(branch))
        legacy_pdu_gauge_metrics.append('snmp.humidityProbe{}'.format(branch))
        for xyz in ['xy', 'yz', 'zx']:
            legacy_pdu_monotonic_count_metrics.append('snmp.energy{}{}s'.format(xyz, branch))
            legacy_pdu_gauge_metrics.append('snmp.voltage{}{}'.format(xyz, branch))
            legacy_pdu_gauge_metrics.append('snmp.power{}{}'.format(xyz, branch))
            legacy_pdu_gauge_metrics.append('snmp.powerFact{}{}'.format(xyz, branch))
            legacy_pdu_gauge_metrics.append('snmp.current{}{}'.format(xyz, branch))
    for branch in range(1, 25):
        legacy_pdu_monotonic_count_metrics.append('snmp.receptacleEnergyoutlet{}s'.format(branch))
        legacy_pdu_gauge_metrics.append('snmp.outlet{}Current'.format(branch))

    for metric in legacy_pdu_gauge_metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, tags=legacy_pdu_tags, count=1)
    for metric in legacy_pdu_monotonic_count_metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.MONOTONIC_COUNT, tags=legacy_pdu_tags, count=1)

    # New metrics
    pdu_tags = common_tags + [
        'pdu_cabinetid:cab1',
        'pdu_ipaddress:42.2.210.224',
        'pdu_macaddress:0x111111111111',
        'pdu_model:model1',
        'pdu_name:name1',
        'pdu_version:v1.1',
    ]
    aggregator.assert_metric('snmp.cpiPduNumberBranches', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduNumberOutlets', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduOutOfService', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduUpgrade', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduChainRole', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduTotalPower', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)

    for lock in [1, 2]:
        lock_tags = common_tags + ['lock_id:{}'.format(lock)]
        aggregator.assert_metric('snmp.cpiPduEasStatus', metric_type=aggregator.GAUGE, tags=lock_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduDoorStatus', metric_type=aggregator.GAUGE, tags=lock_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduLockStatus', metric_type=aggregator.GAUGE, tags=lock_tags, count=1)

    for sensor_name, sensor_index in [('sensor1', 8), ('sensor2', 20)]:
        sensor_tags = common_tags + [
            'sensor_index:{}'.format(sensor_index),
            'sensor_name:{}'.format(sensor_name),
            'sensor_type:1',
        ]
        aggregator.assert_metric('snmp.cpiPduSensorValue', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)

    for line in [7, 14]:
        line_tags = common_tags + ['line_id:{}'.format(line)]
        aggregator.assert_metric('snmp.cpiPduLineCurrent', metric_type=aggregator.GAUGE, tags=line_tags, count=1)

    for branch in [7, 11]:
        branch_tags = common_tags + ['branch_id:{}'.format(branch), 'pdu_name:name1']
        aggregator.assert_metric('snmp.cpiPduBranchCurrent', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduBranchMaxCurrent', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduBranchVoltage', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduBranchPower', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric(
            'snmp.cpiPduBranchPowerFactor', metric_type=aggregator.GAUGE, tags=branch_tags, count=1
        )
        aggregator.assert_metric('snmp.cpiPduBranchStatus', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric(
            'snmp.cpiPduBranchEnergy', metric_type=aggregator.MONOTONIC_COUNT, tags=branch_tags, count=1
        )

    for branch in [11]:
        branch_tags = common_tags + ['branch_id:{}'.format(branch), 'pdu_name:name1']
        aggregator.assert_metric(
            'snmp.cpiPduBranchPowerFactor', metric_type=aggregator.GAUGE, tags=branch_tags, count=1
        )

        aggregator.assert_metric(
            'snmp.cpiPduBranchEnergy', metric_type=aggregator.MONOTONIC_COUNT, tags=branch_tags, count=1
        )

    for outlet_id, outlet_branch, outlet_name in [(5, 17, 'outlet1'), (22, 4, 'outlet2')]:
        outlet_tags = common_tags + [
            'outlet_id:{}'.format(outlet_id),
            'outlet_branchid:{}'.format(outlet_branch),
            'outlet_name:{}'.format(outlet_name),
        ]
        aggregator.assert_metric('snmp.cpiPduOutletCurrent', metric_type=aggregator.GAUGE, tags=outlet_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduOutletVoltage', metric_type=aggregator.GAUGE, tags=outlet_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduOutletPower', metric_type=aggregator.GAUGE, tags=outlet_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduOutletStatus', metric_type=aggregator.GAUGE, tags=outlet_tags, count=1)
        aggregator.assert_metric(
            'snmp.cpiPduOutletEnergy', metric_type=aggregator.MONOTONIC_COUNT, tags=outlet_tags, count=1
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_isilon(aggregator):
    run_profile_check('isilon')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:isilon',
        'cluster_name:testcluster1',
        'node_name:node1',
        'node_type:1',
        'device_vendor:dell',
    ]

    cluster_rates = [
        'clusterIfsInBytes',
        'clusterIfsOutBytes',
    ]

    node_rates = [
        'nodeIfsOutBytes',
        'nodeIfsInBytes',
    ]

    protocol_metrics = [
        'protocolOpsPerSecond',
        'latencyMin',
        'latencyMax',
        'latencyAverage',
    ]

    quota_metrics = ['quotaHardThreshold', 'quotaSoftThreshold', 'quotaUsage', 'quotaAdvisoryThreshold']

    quota_ids_types = [
        (422978632, 1),
        (153533730, 5),
        (3299369987, 4),
        (2149993012, 3),
        (1424325378, 1),
        (4245321451, 0),
        (2328145711, 1),
        (1198032230, 4),
        (1232918362, 1),
        (1383990869, 1),
    ]

    common.assert_common_metrics(aggregator, common_tags)

    for metric in quota_metrics:
        for qid, qtype in quota_ids_types:
            tags = ['quota_id:{}'.format(qid), 'quota_type:{}'.format(qtype)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)

    for metric in protocol_metrics:
        for num in range(1, 3):
            tags = ['protocol_name:testprotocol{}'.format(num)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_metric('snmp.clusterHealth', metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in cluster_rates:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=common_tags, count=1)

    aggregator.assert_metric('snmp.nodeHealth', metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in node_rates:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=common_tags, count=1)

    for fan in [4, 6, 10, 11, 14, 21, 22, 23, 25, 30]:
        tags = ['fan_name:testfan', 'fan_number:{}'.format(fan)] + common_tags
        aggregator.assert_metric('snmp.fanSpeed', metric_type=aggregator.GAUGE, tags=tags, count=1)

    for status, bay in [('SMARTFAIL', 1), ('HEALTHY', 2), ('DEAD', 3)]:
        tags = common_tags + ['disk_status:{}'.format(status), 'disk_bay:{}'.format((bay))]
        aggregator.assert_metric('snmp.diskSizeBytes', metric_type=aggregator.RATE, tags=tags)

    aggregator.assert_metric('snmp.ifsUsedBytes', metric_type=aggregator.RATE, tags=common_tags, count=1)
    aggregator.assert_metric('snmp.ifsTotalBytes', metric_type=aggregator.RATE, tags=common_tags, count=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_apc_ups(aggregator):
    run_profile_check('apc_ups')
    profile_tags = [
        'snmp_profile:apc_ups',
        'model:APC Smart-UPS 600',
        'firmware_version:2.0.3-test',
        'serial_num:test_serial',
        'ups_name:testIdentName',
        'device_vendor:apc',
    ]

    tags = common.CHECK_TAGS + profile_tags

    common.assert_common_metrics(aggregator, tags)

    for metric in metrics.APC_UPS_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    aggregator.assert_metric(
        'snmp.upsOutletGroupStatusGroupState',
        metric_type=aggregator.GAUGE,
        tags=[
            'outlet_group_name:test_outlet',
            'ups_outlet_group_status_group_state:3',
        ]
        + tags,
    )

    for metric, value in metrics.APC_UPS_UPS_BASIC_STATE_OUTPUT_STATE_METRICS:
        aggregator.assert_metric(metric, value=value, metric_type=aggregator.GAUGE, count=1, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_fortinet_fortigate(aggregator):
    run_profile_check('fortinet-fortigate')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:fortinet-fortigate',
        'device_vendor:fortinet',
        'snmp_host:fortinet-fortigate.device.name',
        'device_hostname:fortinet-fortigate.device.name',
    ]

    common_gauge_metrics = [
        'fgSysCpuUsage',
        'fgSysMemUsage',
        'fgSysMemCapacity',
        'fgSysLowMemUsage',
        'fgSysLowMemCapacity',
        'fgSysDiskUsage',
        'fgSysDiskCapacity',
        'fgSysSesCount',
        'fgSysSesRate1',
        'fgSysSes6Count',
        'fgSysSes6Rate1',
        'fgApHTTPConnections',
        'fgApHTTPMaxConnections',
        'fgVdNumber',
        'fgVdMaxVdoms',
    ]

    processor_gauge_metrics = [
        'fgProcessorUsage',
        'fgProcessorSysUsage',
    ]
    processor_count_metrics = [
        'fgProcessorPktRxCount',
        'fgProcessorPktTxCount',
        'fgProcessorPktDroppedCount',
    ]
    processor_tags = common_tags + ['processor_index:12']

    phase1_name = [
        'ESMAO-Lomtec',
        'ESMAO',
    ]

    vd_metrics = [
        'fgVdEntOpMode',
        'fgVdEntHaState',
        'fgVdEntCpuUsage',
        'fgVdEntMemUsage',
        'fgVdEntSesCount',
        'fgVdEntSesRate',
    ]
    vd_tags = common_tags + ['virtualdomain_index:4', 'virtualdomain_name:their oxen quaintly']

    common.assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)

    for metric in common_gauge_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in processor_gauge_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=processor_tags, count=1)
    for metric in processor_count_metrics:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=processor_tags, count=1
        )
        aggregator.assert_metric(
            'snmp.{}.rate'.format(metric), metric_type=aggregator.RATE, tags=processor_tags, count=1
        )

    for metric in vd_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=vd_tags, count=1)

    # Interface
    aggregator.assert_metric('snmp.fgIntfEntVdom', metric_type=aggregator.GAUGE, count=1)

    for name in phase1_name:
        tags = common_tags + ['vpn_tunnel:' + name]
        aggregator.assert_metric('snmp.fgVpnTunEntInOctets', metric_type=aggregator.RATE, tags=tags, count=1)
        aggregator.assert_metric('snmp.fgVpnTunEntOutOctets', metric_type=aggregator.RATE, tags=tags, count=1)
        aggregator.assert_metric('snmp.fgVpnTunEntStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    # Firewall
    firewall_tags = common_tags + ['policy_index:22', 'virtualdomain_index:2']
    for metric in ['fgFwPolPktCount', 'fgFwPolByteCount']:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=firewall_tags, count=1
        )
        aggregator.assert_metric(
            'snmp.{}.rate'.format(metric), metric_type=aggregator.RATE, tags=firewall_tags, count=1
        )

    # Firewall 6
    firewall6_tags = common_tags + ['policy6_index:29', 'virtualdomain_index:5']
    for metric in ['fgFwPol6PktCount', 'fgFwPol6ByteCount']:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=firewall6_tags, count=1
        )
        aggregator.assert_metric(
            'snmp.{}.rate'.format(metric), metric_type=aggregator.RATE, tags=firewall6_tags, count=1
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_netapp(aggregator):
    run_profile_check('netapp')

    profile_tags = [
        'snmp_profile:netapp',
        'snmp_host:example-datacenter.company',
        'device_hostname:example-datacenter.company',
        'device_vendor:netapp',
    ]

    common_tags = common.CHECK_TAGS + profile_tags

    common.assert_common_metrics(aggregator, common_tags)

    gauges = [
        'cfInterconnectStatus',
        'miscCacheAge',
        'ncHttpActiveCliConns',
    ]
    counts = [
        'extcache64Hits',
    ]
    for metric in gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    snapvault_counts = [
        'svTotalFailures',
    ]
    snapvaults = [('5', '/vol/dir1', '5'), ('6', '/vol/dir3', '2'), ('18', '/vol/dir9', '4')]
    for metric in snapvault_counts:
        for index, destination, state in snapvaults:
            tags = [
                'index:{}'.format(index),
                'destination:{}'.format(destination),
                'state:{}'.format(state),
            ] + common_tags
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    snapmirrors = [('6', '1'), ('9', '5'), ('29', '1')]
    snapmirror_gauges = [
        'snapmirrorLag',
    ]
    snapmirror_counts = [
        'snapmirrorTotalFailures',
    ]
    for index, state in snapmirrors:
        tags = ['index:{}'.format(index), 'state:{}'.format(state)] + common_tags
        for metric in snapmirror_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in snapmirror_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    filesystem_gauges = [
        'dfHighTotalKBytes',
        'dfHighAvailKBytes',
        'dfInodesUsed',
        'dfInodesFree',
    ]
    filesystem_indexes = [
        '1022',
        '1023',
        '1024',
        '1025',
        '1026',
        '1027',
        '1028',
        '1029',
        '1032',
        '1033',
    ]
    filesystems = ['/vol/dir{}'.format(n) for n in range(1, len(filesystem_indexes) + 1)]
    for metric in filesystem_gauges:
        for index, filesystem in zip(filesystem_indexes, filesystems):
            tags = ['index:{}'.format(index), 'filesystem:{}'.format(filesystem)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    if_counts = [
        'ifHighInOctets',
    ]
    if_rates = [
        'ifHighInOctets.rate',
    ]
    interfaces = [
        # Interface descriptions will be normalized in the backend, but we receive the raw DisplayString values here.
        ('6', 'netgear ifX300 v1'),
        ('7', 'junyper proto12 12.3'),
        ('23', 'malabar yz42 10.2020'),
    ]
    for index, descr in interfaces:
        tags = ['index:{}'.format(index), 'interface:{}'.format(descr)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_rates:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.usefixtures("dd_environment")
def test_cisco_catalyst(aggregator):
    run_profile_check('cisco-catalyst')
    common_tags = common.CHECK_TAGS + [
        'snmp_host:catalyst-6000.example',
        'device_hostname:catalyst-6000.example',
        'snmp_profile:cisco-catalyst',
        'device_vendor:cisco',
    ]

    sensors = [5, 9]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:10'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)
    interfaces = ["Gi1/0/{}".format(i) for i in [6, 10, 12, 18, 22, 25, 27]]
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in CIE_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    frus = [1001, 1010, 2001, 2010]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in FRU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    common.assert_common_metrics(aggregator, common_tags)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.parametrize("file", ["juniper-ex", "juniper-ex-variation"])
@pytest.mark.usefixtures("dd_environment")
def test_juniper_ex(aggregator, file):
    run_profile_check(file, 'juniper-ex')
    common_tags = common.CHECK_TAGS + [
        'snmp_profile:juniper-ex',
        'device_vendor:juniper-networks',
    ]
    _check_juniper_virtual_chassis(aggregator, common_tags)
    _check_juniper_dcu(aggregator, common_tags)
    _check_juniper_cos(aggregator, common_tags)
    _check_juniper_firewall(aggregator, common_tags)
    _check_bgp4(aggregator, common_tags)
    common.assert_common_metrics(aggregator, common_tags)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.parametrize("file", ["juniper-mx", "juniper-mx-variation"])
@pytest.mark.usefixtures("dd_environment")
def test_juniper_mx(aggregator, file):
    run_profile_check(file, 'juniper-mx')
    common_tags = common.CHECK_TAGS + [
        'snmp_profile:juniper-mx',
        'device_vendor:juniper-networks',
    ]
    _check_juniper_virtual_chassis(aggregator, common_tags)
    _check_juniper_firewall(aggregator, common_tags)
    _check_bgp4(aggregator, common_tags)
    common.assert_common_metrics(aggregator, common_tags)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.parametrize("file", ["juniper-srx", "juniper-srx-variation"])
@pytest.mark.usefixtures("dd_environment")
def test_juniper_srx(aggregator, file):
    run_profile_check(file, 'juniper-srx')
    common_tags = common.CHECK_TAGS + [
        'snmp_profile:juniper-srx',
        'device_vendor:juniper-networks',
    ]
    _check_juniper_userfirewall(aggregator, common_tags)
    _check_juniper_dcu(aggregator, common_tags)
    _check_juniper_scu(aggregator, common_tags)
    _check_bgp4(aggregator, common_tags)
    common.assert_common_metrics(aggregator, common_tags)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def _check_juniper_scu(aggregator, common_tags):
    """
    Shared testing function for Juniper profiles supporting scu
    """
    scu_tags = [
        ['address_family:1', 'interface:kept but'],
        ['address_family:1', 'interface:quaintly driving oxen their zombies oxen acted acted'],
        ['address_family:1', 'interface:but forward kept but their driving oxen quaintly acted'],
    ]
    for metric in SCU_COUNTS:
        for tags in scu_tags:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags + tags, count=1
            )


def _check_juniper_userfirewall(aggregator, common_tags):
    """
    Shared testing function for Juniper profiles supporting userfirewall (user auth)
    """
    userfirewall_tags = [
        ['ldap_domain_name:Mycroft Holmes', 'ldap_host:brother'],
        ['ldap_domain_name:Jim Moriarty', 'ldap_host:enemy'],
    ]
    for metric in USER_FIREWALL:
        for tags in userfirewall_tags:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags + tags, count=1
            )


def _check_juniper_dcu(aggregator, common_tags):
    """
    Shared testing function for Juniper profiles supporting DCU
    """
    dcu_tags = [
        [
            'address_family:1',
            'destination_class_name:their',
            'interface:quaintly driving oxen their zombies oxen acted acted',
        ],
        [
            'address_family:1',
            'destination_class_name:acted but forward acted zombies forward',
            'interface:but forward kept but their driving oxen quaintly acted',
        ],
        [
            'address_family:2',
            'destination_class_name:oxen Jaded oxen Jaded forward kept quaintly',
            'interface:kept but',
        ],
    ]
    for decu_metric in DCU_COUNTS:
        for tags in dcu_tags:
            aggregator.assert_metric(
                'snmp.{}'.format(decu_metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags + tags, count=1
            )


def _check_juniper_firewall(aggregator, common_tags):
    """
    Shared testing function for Juniper profiles supporting firewall metrics
    """
    firewall_tags = [
        [
            'counter_name:Jaded oxen kept their driving but kept',
            'counter_type:4',
            'firewall_filter_name:their driving quaintly but Jaded oxen',
        ],
        [
            'counter_name:but but but their their their kept kept forward',
            'counter_type:4',
            'firewall_filter_name:driving kept acted Jaded zombies kept acted',
        ],
    ]
    for metric in FIREWALL_COUNTS:
        for tags in firewall_tags:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=common_tags + tags,
                count=1,
            )


def _check_juniper_virtual_chassis(aggregator, common_tags):
    """
    Shared testing function for Juniper profiles supporting virtual chassis metrics
    """
    virtual_chassis_tags = [
        ['port_name:but driving but'],
        ['port_name:Jaded forward but oxen quaintly their their'],
        ['port_name:forward forward driving driving Jaded Jaded'],
    ]

    for count_and_rate_metric in VIRTUAL_CHASSIS_COUNTS:
        for tags in virtual_chassis_tags:
            aggregator.assert_metric(
                'snmp.{}'.format(count_and_rate_metric),
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=common_tags + tags,
                count=1,
            )
    for rate_metric in VIRTUAL_CHASSIS_RATES:
        for tags in virtual_chassis_tags:
            aggregator.assert_metric(
                'snmp.{}'.format(rate_metric), metric_type=aggregator.GAUGE, tags=common_tags + tags, count=1
            )


def _check_juniper_cos(aggregator, common_tags):
    """
    Shared testing function for Juniper profiles supporting COS metrics
    """
    cos_tags = [
        ['interface:acted oxen oxen forward quaintly kept zombies but oxen', 'queue_number:25'],
        ['interface:acted kept quaintly acted oxen kept', 'queue_number:50'],
        ['interface:their', 'queue_number:15'],
    ]
    for cos_metric in COS_COUNTS:
        for tags in cos_tags:
            aggregator.assert_metric(
                'snmp.{}'.format(cos_metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags + tags, count=1
            )
    for cos_metric in COS_RATES:
        for tags in cos_tags:
            aggregator.assert_metric(
                'snmp.{}'.format(cos_metric), metric_type=aggregator.GAUGE, tags=common_tags + tags, count=1
            )


def _check_bgp4(aggregator, common_tags):
    """
    Shared testing function for profiles supporting BGP4 metrics.
    """
    tags = ['neighbor:244.12.239.177', 'remote_as:26', 'admin_status:2', 'peer_state:6'] + common_tags
    for metric in PEER_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    for metric in PEER_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags)


@pytest.mark.usefixtures("dd_environment")
def test_cisco_asr_1001x(aggregator):
    run_profile_check(recording_name='cisco-asr-1001x', profile_name='cisco-asr')
    common_tags = common.CHECK_TAGS + [
        'snmp_profile:cisco-asr',
        'device_vendor:cisco',
    ]
    common.assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysUpTimeInstance', metric_type=aggregator.GAUGE, tags=common_tags)

    _check_common_asr(aggregator, common_tags + ['interface:eth/0', 'interface_index:3'])

    for metric in TCP_COUNTS + ['udpInErrors', 'udpNoPorts']:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.tcpCurrEstab', metric_type=aggregator.GAUGE, tags=common_tags)

    for metric in IP_COUNTS + IPX_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags + ['ipversion:ipv6']
        )
    for metric in IP_IF_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric),
            metric_type=aggregator.MONOTONIC_COUNT,
            tags=common_tags + ['ipversion:ipv6', 'interface:1'],
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_cisco_asr_9001(aggregator):
    run_profile_check(recording_name='cisco-asr-9001', profile_name='cisco-asr')
    common_tags = common.CHECK_TAGS + [
        'snmp_profile:cisco-asr',
        'device_vendor:cisco',
    ]
    common.assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysUpTimeInstance', metric_type=aggregator.GAUGE, tags=common_tags)

    _check_common_asr(aggregator, tags=common_tags + ['interface:eth/0', 'interface_index:19'])
    for metric in TCP_COUNTS + ['udpInErrors', 'udpNoPorts']:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.tcpCurrEstab', metric_type=aggregator.GAUGE, tags=common_tags)

    IP_SYS_METRICS = [
        'ipSystemStatsInAddrErrors',
        'ipSystemStatsInDiscards',
        'ipSystemStatsInHdrErrors',
        'ipSystemStatsInNoRoutes',
        'ipSystemStatsInTruncatedPkts',
        'ipSystemStatsInUnknownProtos',
        'ipSystemStatsOutDiscards',
        'ipSystemStatsOutFragCreates',
        'ipSystemStatsOutFragFails',
        'ipSystemStatsOutFragOKs',
        'ipSystemStatsOutFragReqds',
        'ipSystemStatsOutNoRoutes',
        'ipSystemStatsReasmFails',
        'ipSystemStatsReasmOKs',
        'ipSystemStatsReasmReqds',
    ]
    for metric in IP_SYS_METRICS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags + ['ipversion:ipv6']
        )

    IP_IF_METRICS = [
        'ipIfStatsHCInMcastOctets',
        'ipIfStatsHCInMcastPkts',
        'ipIfStatsHCInOctets',
        'ipIfStatsHCOutMcastOctets',
        'ipIfStatsHCOutMcastPkts',
        'ipIfStatsHCOutOctets',
        'ipIfStatsHCOutTransmits',
    ]
    for metric in IP_IF_METRICS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric),
            metric_type=aggregator.MONOTONIC_COUNT,
            tags=common_tags + ['ipversion:ipv6', 'interface:45'],
        )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def test_cisco_asr_9901(aggregator):
    run_profile_check(recording_name='cisco-asr-9901', profile_name='cisco-asr')
    common_tags = common.CHECK_TAGS + [
        'snmp_profile:cisco-asr',
        'device_vendor:cisco',
    ]
    common.assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysUpTimeInstance', metric_type=aggregator.GAUGE, tags=common_tags)

    _check_common_asr(aggregator, common_tags + ['interface:eth0', 'interface_index:39'])

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


def _check_common_asr(aggregator, tags):
    """
    Shared testing function for cisco ASR profiles.
    """
    GAUGE_METRICS = [
        'ifAdminStatus',
        'ifOperStatus',
        'ifSpeed',
    ]
    COUNTS_METRICS = [
        'ifInErrors',
        'ifInDiscards',
        'ifOutErrors',
        'ifOutDiscards',
    ]
    RATE_METRICS = ['ifInErrors.rate', 'ifInDiscards.rate', 'ifOutErrors.rate', 'ifOutDiscards.rate']

    for metric in GAUGE_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    for metric in COUNTS_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags)

    for metric in RATE_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags)
