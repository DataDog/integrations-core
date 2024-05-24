# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import yaml

from .. import common

# We are excluding some tags like `device_vendor` since:
# - it's not part of the main purpose of assert_all_profile_metrics_and_tags_covered
# - and asserting `device_vendor` would require scanning recursively the profile (adds complexity to the assertion code)
ASSERT_ALL_PROFILE_EXCLUDED_TAGS = {'device_vendor'}


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


def assert_extend_aruba_switch_cpu_memory(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.4.1.14823.2.2.1.2.1.13.1.3.4|66|29
    """
    # fmt: on
    aggregator.assert_metric("snmp.cpu.usage", metric_type=aggregator.GAUGE, tags=common_tags + ['cpu:4'])


def assert_extend_fortinet_fortigate_cpu_memory(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.4.1.12356.101.4.1.3.0|66|10
    """
    # fmt: on
    aggregator.assert_metric("snmp.cpu.usage", metric_type=aggregator.GAUGE, tags=common_tags)


def assert_extend_fortinet_fortigate_vpn_tunnel(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.4.1.12356.101.12.2.2.1.2.2|4|ESMAO
1.3.6.1.4.1.12356.101.12.2.2.1.20.2|2|1
    """
    # fmt: on
    aggregator.assert_metric(
        'snmp.fgVpnTunEntStatus', metric_type=aggregator.GAUGE, tags=common_tags + ['vpn_tunnel:ESMAO']
    )


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
1.3.6.1.2.1.4.31.1.1.4.1|70|310637142
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


def assert_extend_cisco_generic(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.4.1.9.9.13.1.4.1.1.11|2|11
1.3.6.1.4.1.9.9.13.1.4.1.3.11|2|6
    """
    # fmt: on
    aggregator.assert_metric(
        'snmp.ciscoEnvMonFanStatus',
        metric_type=aggregator.GAUGE,
        tags=common_tags + ['fan_state:not_functioning', 'fan_status_index:11'],
    )
    aggregator.assert_metric(
        'snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=common_tags + ['fan_status_index:11']
    )


def assert_extend_generic_host_resources_base(aggregator, common_tags):
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
1.3.6.1.2.1.25.3.3.1.2.21|2|15
"""
    # fmt: on
    aggregator.assert_metric("snmp.hrSystemUptime", metric_type=aggregator.GAUGE, tags=common_tags)

    cpu_rows = [('10', '10'), ('21', '21')]
    for cpu_row in cpu_rows:
        processorid, hr_device_index = cpu_row
        aggregator.assert_metric(
            'snmp.hrProcessorLoad',
            metric_type=aggregator.GAUGE,
            tags=common_tags + ['processorid:' + processorid, 'hr_device_index:' + hr_device_index],
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
1.3.6.1.2.1.25.3.3.1.2.21|2|15
"""
    # fmt: on
    assert_extend_generic_host_resources_cpu_mem(aggregator, common_tags)
    assert_extend_generic_host_resources_base(aggregator, common_tags)


def assert_extend_generic_entity_sensor(aggregator, common_tags):
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
    aggregator.assert_metric("snmp.ucd.memTotalSwap", metric_type=aggregator.GAUGE, tags=common_tags)


def assert_extend_checkpoint_firewall_cpu_memory(aggregator, common_tags):
    # fmt:off
    """Add the following to the snmprec
1.3.6.1.4.1.2620.1.6.7.4.3.0|70|15569114139837823111
    """
    # fmt:on
    aggregator.assert_metric("snmp.memory.total", metric_type=aggregator.GAUGE, tags=common_tags)


def assert_extend_cisco(aggregator, common_tags):
    # fmt:off
    """Add the following to the snmprec
1.3.6.1.4.1.9.9.109.1.1.1.1.12.712|66|353
    """
    # fmt:on
    tags = ['cpu:712']
    aggregator.assert_metric("snmp.cpmCPUMemoryUsed", metric_type=aggregator.GAUGE, tags=common_tags + tags)


def assert_extend_generic_ups(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.33.1.2.2.0|2|10
    """
    # fmt: on
    aggregator.assert_metric('snmp.upsSecondsOnBattery', metric_type=aggregator.GAUGE, tags=common_tags)


def assert_extend_juniper_cos(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.4.1.2636.3.15.9.1.2.170|4|jnxCosIfsetDescr value1
1.3.6.1.4.1.2636.3.15.10.1.3.170.25|70|12770856836917969245
1.3.6.1.4.1.2636.3.15.10.1.2.170.25|2|25
    """
    # fmt: on
    tags = ['interface:jnxCosIfsetDescr value1', 'queue_number:25'] + common_tags
    aggregator.assert_metric('snmp.jnxCosIfsetQstatQedPkts', metric_type=aggregator.COUNT, tags=tags)


def assert_extend_juniper_dcu(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.2.1.31.1.1.1.1.83|4|eth111
1.3.6.1.4.1.2636.3.6.2.1.4.83.1.5.116.104.101.105.114|70|12317383665498203792
    """
    # fmt: on
    tags = ['interface:eth111'] + common_tags
    aggregator.assert_metric('snmp.jnxDcuStatsPackets', metric_type=aggregator.COUNT, tags=tags)


def assert_extend_juniper_firewall(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.4.1.2636.3.5.2.1.1.37.116.104.101.105.114.32.100.114.105.118.105.110.103.32.113.117.97.105.110.116.108.121.32.98.117.116.32.74.97.100.101.100.32.111.120.101.110.38.74.97.100.101.100.32.111.120.101.110.32.107.101.112.116.32.116.104.101.105.114.32.100.114.105.118.105.110.103.32.98.117.116.32.107.101.112.116.4|4|filter111
1.3.6.1.4.1.2636.3.5.2.1.4.37.116.104.101.105.114.32.100.114.105.118.105.110.103.32.113.117.97.105.110.116.108.121.32.98.117.116.32.74.97.100.101.100.32.111.120.101.110.38.74.97.100.101.100.32.111.120.101.110.32.107.101.112.116.32.116.104.101.105.114.32.100.114.105.118.105.110.103.32.98.117.116.32.107.101.112.116.4|70|4454094099404974412
    """
    # fmt: on
    tags = ['firewall_filter_name:filter111'] + common_tags
    aggregator.assert_metric('snmp.jnxFWCounterPacketCount', metric_type=aggregator.COUNT, tags=tags)


def assert_extend_juniper_virtualchassis(aggregator, common_tags):
    # fmt: off
    """Add the following to the snmprec
1.3.6.1.4.1.2636.3.40.1.4.1.2.1.2.11.43.74.97.100.101.100.32.102.111.114.119.97.114.100.32.98.117.116.32.111.120.101.110.32.113.117.97.105.110.116.108.121.32.116.104.101.105.114.32.116.104.101.105.114|4|port111
1.3.6.1.4.1.2636.3.40.1.4.1.2.1.5.11.43.74.97.100.101.100.32.102.111.114.119.97.114.100.32.98.117.116.32.111.120.101.110.32.113.117.97.105.110.116.108.121.32.116.104.101.105.114.32.116.104.101.105.114|70|12189304536513319332
    """
    # fmt: on
    tags = ['port_name:port111'] + common_tags
    aggregator.assert_metric('snmp.jnxVirtualChassisPortInPkts', metric_type=aggregator.COUNT, tags=tags)


def assert_all_profile_metrics_and_tags_covered(profile, aggregator):
    metric_and_tags = collect_profile_metrics_and_tags(profile)
    global_tags = set(
        metric_and_tags["global_tags"]
        + ['device_namespace', 'snmp_device', 'snmp_host', 'snmp_profile', 'device_id', 'device_ip', 'device_hostname']
    )

    for metric, metric_info in metric_and_tags["table_metrics"].items():
        collected_metric_tag_keys = get_collected_metric_tag_keys(aggregator, metric) - ASSERT_ALL_PROFILE_EXCLUDED_TAGS
        expected_metric_tag_keys = global_tags | set(metric_info.get('tags'))
        assert (
            collected_metric_tag_keys == expected_metric_tag_keys
        ), "collected and profile metric tags differ for metric `{}`".format(metric)
    for metric in metric_and_tags["scalar_metrics"]:
        assert len(aggregator.metrics('snmp.' + metric)) > 0
        for collected_metric in aggregator.metrics('snmp.' + metric):
            tag_keys = tags_to_tag_keys(collected_metric.tags) - ASSERT_ALL_PROFILE_EXCLUDED_TAGS
            assert tag_keys == global_tags, "collected and profile metric tags differ for metric `{}`".format(metric)


def get_collected_metric_tag_keys(aggregator, metric):
    collected_metrics = aggregator.metrics('snmp.' + metric)
    collected_metric_tags = set()
    for collected_metric in collected_metrics:
        collected_metric_tags |= set(collected_metric.tags)
    return tags_to_tag_keys(collected_metric_tags)


def tags_to_tag_keys(tags):
    tag_keys = set()
    for tag in tags:
        tag_keys.add(tag.split(':', maxsplit=1)[0])
    return tag_keys


def collect_profile_metrics_and_tags(profile):
    profile_path = os.path.join(
        common.HERE, "..", "datadog_checks", "snmp", "data", "default_profiles", profile + ".yaml"
    )
    with open(profile_path, 'r') as profile_file:
        profile_obj = yaml.safe_load(profile_file)
    global_tags = []
    for global_tag in profile_obj.get("metric_tags", []):
        tag = global_tag.get('tag')
        assert tag is not None, 'invalid tag field in {}'.format(global_tag)
        assert tag != '', 'invalid tag field in {}'.format(global_tag)
        global_tags.append(tag)
    table_metrics = {}
    scalar_metrics = {}
    for global_tag in profile_obj.get("metrics", []):
        table = global_tag.get('table')
        symbols = global_tag.get('symbols')
        if symbols:
            metric_tags = global_tag.get('metric_tags', [])
            assert len(metric_tags) > 0, "table metrics must have at least one tag (table: {})".format(table)

            tags = []
            for metric_tag in metric_tags:
                tag = metric_tag.get('tag')
                if tag:
                    tags.append(tag)

            for symbol in symbols:
                name = symbol.get('name')
                table_metrics[name] = {
                    "tags": tags,
                }
        else:
            symbol = global_tag.get('symbol', {}).get('name')
            if symbol:
                scalar_metrics[symbol] = {}
    return {
        "global_tags": global_tags,
        "scalar_metrics": scalar_metrics,
        "table_metrics": table_metrics,
    }
