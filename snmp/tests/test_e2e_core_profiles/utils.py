# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .. import common


def create_e2e_core_test_config(community_string):
    """
    The community_string must correspond to a .snmprec file name.
    It is used to tell snmpsim to use the corresponding .snmprec file.
    """
    config = common.generate_container_instance_config([])
    config["init_config"]["loader"] = "core"
    instance = config["instances"][0]
    instance.update({"community_string": community_string})
    return config


def get_device_ip_from_config(config):
    return config["instances"][0]["ip_address"]


def assert_common_metrics(aggregator, common_tags):
    common.assert_common_metrics(aggregator, tags=common_tags, is_e2e=True, loader="core")


def assert_extend_generic_if(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.2.1.0|2|28
    """
    # fmt: on
    aggregator.assert_metric("snmp.ifNumber", metric_type=aggregator.GAUGE, tags=common_tags)


def assert_extend_generic_ip(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.4.31.1.1.4.1 = Counter64: 310637142
    """
    # fmt: on
    aggregator.assert_metric(
        "snmp.ipSystemStatsHCInReceives",
        metric_type=aggregator.COUNT,
        tags=common_tags + ["ipversion:ipv4"],
    )


def assert_extend_generic_tcp(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.6.5.0|65|4698
    """
    # fmt: on
    aggregator.assert_metric("snmp.tcpActiveOpens", metric_type=aggregator.COUNT, tags=common_tags)


def assert_extend_generic_udp(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.7.8.0|70|6116206687099577350
    """
    # fmt: on
    aggregator.assert_metric("snmp.udpHCInDatagrams", metric_type=aggregator.COUNT, tags=common_tags)


def assert_extend_generic_ospf(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.14.10.1.6.192.29.116.26.0|2|8
    """
    # fmt: on
    aggregator.assert_metric(
        "snmp.ospfNbr", metric_type=aggregator.GAUGE, tags=common_tags + ["neighbor_state:full"], value=1
    )
    aggregator.assert_metric(
        "snmp.ospfNbrState", metric_type=aggregator.GAUGE, tags=common_tags + ["neighbor_state:full"]
    )


def assert_extend_generic_bgp4(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.15.3.1.3.244.12.239.177|2|2
    """
    # fmt: on
    aggregator.assert_metric(
        "snmp.bgpPeerAdminStatus",
        metric_type=aggregator.GAUGE,
        tags=common_tags + ["admin_status:start"],
    )
    aggregator.assert_metric(
        "snmp.peerConnectionByState",
        metric_type=aggregator.GAUGE,
        tags=common_tags + ["admin_status:start"],
        value=1,
    )


def assert_extend_cisco_cpu_memory(aggregator, common_tags):
    aggregator.assert_metric("snmp.memory.used", metric_type=aggregator.GAUGE, tags=common_tags + ["mem:18"])
    aggregator.assert_metric("snmp.ciscoMemoryPoolUsed", metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric("snmp.cpu.usage", metric_type=aggregator.GAUGE, tags=common_tags + ["cpu:712"])
    aggregator.assert_metric(
        "snmp.cpmCPUTotal1minRev",
        metric_type=aggregator.GAUGE,
        tags=common_tags + ["cpu:712"],
    )


def assert_extend_generic_host_resources_base(aggregator, common_tags):
    aggregator.assert_metric("snmp.hrSystemUptime", metric_type=aggregator.GAUGE, tags=common_tags)

    cpu_rows = ['10', '21']
    for cpu_row in cpu_rows:
        aggregator.assert_metric(
            'snmp.hrProcessorLoad', metric_type=aggregator.GAUGE, tags=common_tags + ['processorid:' + cpu_row]
        )

    hr_mem_rows = [
        ['storagedesc:kept but their Jaded but driving', 'storagetype:1.3.6.1.3.167.36'],
        ['storagedesc:kept but their Jaded but driving', 'storagetype:1.3.6.1.3.167.36'],
    ]
    for mem_row in hr_mem_rows:
        aggregator.assert_metric('snmp.hrStorageSize', metric_type=aggregator.GAUGE, tags=common_tags + mem_row)
        aggregator.assert_metric('snmp.hrStorageUsed', metric_type=aggregator.GAUGE, tags=common_tags + mem_row)


def assert_extend_generic_host_resources_cpu_mem(aggregator, common_tags):
    cpu_rows = ['10', '21']
    for cpu_row in cpu_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + ['cpu:' + cpu_row])

    mem_rows = ['31', '4']
    for mem_row in mem_rows:
        aggregator.assert_metric(
            'snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags + ['mem:' + mem_row]
        )
        aggregator.assert_metric(
            'snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + ['mem:' + mem_row]
        )
        aggregator.assert_metric(
            'snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags + ['mem:' + mem_row]
        )


def assert_extend_generic_host_resources(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.25.1.1.0|67|201526890
1.3.6.1.2.1.25.2.3.1.1.4|2|4
1.3.6.1.2.1.25.2.3.1.1.31|2|31
1.3.6.1.2.1.25.2.3.1.2.4|6|1.3.6.1.3.167.36
1.3.6.1.2.1.25.2.3.1.2.31|6|1.3.6.1.3
1.3.6.1.2.1.25.2.3.1.3.4|4x|6b65707420627574207468656972204a61646564206275742064726976696e67
1.3.6.1.2.1.25.2.3.1.3.31|4x|7a6f6d62696573206f78656e206b657074204a6164656420717561696e746c79207a6f6d62696573
1.3.6.1.2.1.25.2.3.1.5.4|2|17
1.3.6.1.2.1.25.2.3.1.5.31|2|21
1.3.6.1.2.1.25.2.3.1.6.4|2|30
1.3.6.1.2.1.25.2.3.1.6.31|2|4
1.3.6.1.2.1.25.3.3.1.1.10|2|10
1.3.6.1.2.1.25.3.3.1.1.21|2|21
1.3.6.1.2.1.25.3.3.1.2.10|2|31
1.3.6.1.2.1.25.3.3.1.2.21|2|15"""
    # fmt: on
    assert_extend_generic_host_resources_cpu_mem(aggregator, common_tags)
    assert_extend_generic_host_resources_base(aggregator, common_tags)


def assert_extend_entity_sensor(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.99.1.1.1.1.8|2|9
1.3.6.1.2.1.99.1.1.1.2.8|2|7
1.3.6.1.2.1.99.1.1.1.3.8|2|7
1.3.6.1.2.1.99.1.1.1.4.8|2|2
1.3.6.1.2.1.99.1.1.1.5.8|2|3
1.3.6.1.2.1.99.1.1.1.6.8|4x|64726976696e672064726976696e6720666f727761726420616374656420746865697220627574
1.3.6.1.2.1.99.1.1.1.7.8|67|2113891456
1.3.6.1.2.1.99.1.1.1.8.8|66|6698
1.3.6.1.6.3.10.2.1.1.0|4x|4a616465642062757420666f7277617264
1.3.6.1.6.3.10.2.1.2.0|2|31
1.3.6.1.6.3.10.2.1.3.0|2|31
1.3.6.1.6.3.10.2.1.4.0|2|1234
    """
    # fmt: on
    additional_tags = [
        'ent_phy_sensor_oper_status:nonoperational',
        'ent_phy_sensor_precision:7',
        'ent_phy_sensor_scale:micro',
        'ent_phy_sensor_type:percent_rh',
        'ent_phy_sensor_units_display:driving driving forward acted their but',
    ]
    aggregator.assert_metric("snmp.entPhySensorValue", metric_type=aggregator.GAUGE, tags=common_tags + additional_tags)


def assert_extend_generic_ucd(aggregator, common_tags):
    # fmt:off
    """Add the following to the snmprec
1.3.6.1.4.1.2021.4.3.0|2|1048572
    """
    # fmt:on
    aggregator.assert_metric("snmp.memTotalSwap", metric_type=aggregator.GAUGE, tags=common_tags)
