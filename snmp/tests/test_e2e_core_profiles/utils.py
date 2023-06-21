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
    aggregator.assert_metric("snmp.ifNumber", metric_type=aggregator.GAUGE, tags=common_tags)


def assert_extend_generic_ip(aggregator, common_tags):
    aggregator.assert_metric(
        "snmp.ipSystemStatsHCInReceives",
        metric_type=aggregator.COUNT,
        tags=common_tags + ["ipversion:ipv4"],
    )


def assert_extend_generic_tcp(aggregator, common_tags):
    aggregator.assert_metric("snmp.tcpActiveOpens", metric_type=aggregator.COUNT, tags=common_tags)


def assert_extend_generic_udp(aggregator, common_tags):
    aggregator.assert_metric("snmp.udpHCInDatagrams", metric_type=aggregator.COUNT, tags=common_tags)


def assert_extend_generic_ospf(aggregator, common_tags):
    aggregator.assert_metric("snmp.ospfNbrState", metric_type=aggregator.GAUGE, tags=common_tags)


def assert_extend_generic_bgp4(aggregator, common_tags):
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


def assert_extend_generic_host_resources(aggregator, common_tags):
    aggregator.assert_metric("snmp.hrSystemUptime", metric_type=aggregator.GAUGE, tags=common_tags)