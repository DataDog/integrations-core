# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

NS = 'hpe_aruba_edgeconnect'


EXPECTED_METRIC_COUNTS = {
    'device.reachability': 3,
    'device.uptime': 1,
    'device.cpu.usage': 5,
    'device.memory.usage': 5,
    'device.disk.usage': 10,
    'device.hardware.ok': 1,
    'interface.status': 1,
    'interface.speed': 1,
    'interface.bandwidth.tx.count': 3,
    'interface.bandwidth.rx.count': 3,
    'interface.bandwidth.tx.rate': 3,
    'interface.bandwidth.rx.rate': 3,
    'interface.bandwidth.tx.max': 3,
    'interface.bandwidth.rx.max': 3,
    'interface.drops.bytes.tx.count': 3,
    'interface.drops.bytes.rx.count': 3,
    'interface.drops.bytes.tx.rate': 3,
    'interface.drops.bytes.rx.rate': 3,
    'interface.drops.bytes.tx.max': 3,
    'interface.drops.bytes.rx.max': 3,
    'interface.drops.packets.tx.count': 3,
    'interface.drops.packets.rx.count': 3,
    'interface.drops.packets.tx.rate': 3,
    'interface.drops.packets.rx.rate': 3,
    'interface.drops.packets.tx.max': 3,
    'interface.drops.packets.rx.max': 3,
    'interface.utilization.tx.avg': 3,
    'interface.utilization.rx.avg': 3,
    'interface.utilization.tx.max': 3,
    'interface.utilization.rx.max': 3,
    'tunnel.throughput.tx.bps.count': 66,
    'tunnel.throughput.rx.bps.count': 66,
    'tunnel.throughput.tx.bps.rate': 66,
    'tunnel.throughput.rx.bps.rate': 66,
    'tunnel.throughput.tx.pps.count': 66,
    'tunnel.throughput.rx.pps.count': 66,
    'tunnel.throughput.tx.pps.rate': 66,
    'tunnel.throughput.rx.pps.rate': 66,
    'tunnel.throughput.tx.bps.max': 66,
    'tunnel.throughput.rx.bps.max': 66,
    'tunnel.throughput.tx.pps.max': 66,
    'tunnel.throughput.rx.pps.max': 66,
    'tunnel.latency': 33,
    'tunnel.latency.min': 33,
    'tunnel.latency.max': 33,
    'tunnel.loss': 66,
    'tunnel.jitter': 31,
    'tunnel.jitter.max': 31,
    'tunnel.qoe.mos': 62,
    'tunnel.qoe.mos.min': 62,
    'tunnel.status': 31,
    'tunnel.internet_breakout.bandwidth.tx.count': 1,
    'tunnel.internet_breakout.bandwidth.rx.count': 1,
    'tunnel.internet_breakout.bandwidth.tx.rate': 1,
    'tunnel.internet_breakout.bandwidth.rx.rate': 1,
    'tunnel.internet_breakout.bandwidth.tx.max': 1,
    'tunnel.internet_breakout.bandwidth.rx.max': 1,
    'circuit.sla.latency': 4,
    'circuit.sla.loss': 4,
    'circuit.sla.jitter': 4,
    'nexthop.status': 8,
    'qos.class.drops': 4,
    'qos.class.drop.percentage': 2,
    'qos.class.bandwidth.tx.count': 4,
    'qos.class.bandwidth.rx.count': 4,
    'qos.class.bandwidth.tx.rate': 4,
    'qos.class.bandwidth.rx.rate': 4,
    'qos.class.bandwidth.tx.max': 4,
    'qos.class.bandwidth.rx.max': 4,
}


EXPECTED_VALUES = [
    # Device health (from orchestrator + non-archive endpoints).
    ('device.reachability', 1, []),
    ('device.uptime', 86400, []),
    ('device.cpu.usage', 30.0, ['cpu_state:user']),
    ('device.cpu.usage', 15.0, ['cpu_state:system']),
    ('device.cpu.usage', 3.0, ['cpu_state:irq']),
    ('device.cpu.usage', 2.0, ['cpu_state:nice']),
    ('device.cpu.usage', 50.0, ['cpu_state:idle']),
    ('device.memory.usage', 3945080, ['memory_type:total']),
    ('device.memory.usage', 770848, ['memory_type:free']),
    ('device.memory.usage', 3174232, ['memory_type:used']),
    ('device.memory.usage', 2516, ['memory_type:buffers']),
    ('device.memory.usage', 729568, ['memory_type:cached']),
    ('device.disk.usage', 1193348 * 1024, ['mount:/', 'disk_type:used']),
    ('device.disk.usage', 4619060 * 1024, ['mount:/', 'disk_type:free']),
    ('device.disk.usage', 4328968 * 1024, ['mount:/var', 'disk_type:used']),
    ('device.disk.usage', 35553256 * 1024, ['mount:/var', 'disk_type:free']),
    # The fake appliance returns no outstanding HW alarms.
    ('device.hardware.ok', 1, []),
    # Interface status / speed (from /networkInterfaces).
    ('interface.status', 1, ['interface_name:wan0', 'admin_status:up', 'oper_status:up']),
    ('interface.speed', 1000000, ['interface_name:wan0']),
    # Interface bandwidth: wan0 pass-through-unshaped (single-archive aggregation).
    ('interface.bandwidth.tx.count', 79920, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.tx.rate', 1332.0, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.rx.count', 41760, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    # Interface peak: wan0 pass-through-unshaped.
    ('interface.bandwidth.tx.max', 1332, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.rx.max', 696, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    # Tunnel throughput: pass-through-unshaped wan (single-archive aggregation).
    ('tunnel.throughput.tx.bps.count', 38796, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    ('tunnel.throughput.tx.bps.rate', 5172.8, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    ('tunnel.throughput.rx.bps.count', 42456, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    # Tunnel latency: tunnel_12 → to_NewYorkSP01_MPLS1-MPLS1.
    ('tunnel.latency', 1.39, ['tunnel_name:to_NewYorkSP01_MPLS1-MPLS1']),
    ('tunnel.latency.min', 1.38, ['tunnel_name:to_NewYorkSP01_MPLS1-MPLS1']),
    # Tunnel peak: pass-through-unshaped wan.
    ('tunnel.throughput.tx.bps.max', 1272, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    ('tunnel.throughput.rx.bps.max', 1160, ['tunnel_name:pass-through-unshaped', 'side:wan']),
    # Tunnel jitter: bondedTunnel_16 (single sample).
    ('tunnel.jitter', 600, ['tunnel_name:bondedTunnel_16']),
    ('tunnel.jitter.max', 6, ['tunnel_name:bondedTunnel_16']),
    # Tunnel MOS: tunnel_12 (mos_postfec=4.0).
    ('tunnel.qoe.mos', 4.0, ['tunnel_name:tunnel_12', 'fec:post']),
    ('tunnel.qoe.mos.min', 4.0, ['tunnel_name:tunnel_12', 'fec:post']),
    # Tunnel availability: pass-through-unshaped (seconds_down=0).
    ('tunnel.status', 0, ['tunnel_name:pass-through-unshaped']),
    # Internet breakout: wan0 (single-archive aggregation).
    ('tunnel.internet_breakout.bandwidth.tx.count', 38160, ['interface_name:wan0']),
    ('tunnel.internet_breakout.bandwidth.tx.rate', 636.0, ['interface_name:wan0']),
    ('tunnel.internet_breakout.bandwidth.rx.max', 100000, ['interface_name:wan0']),
    # DSCP: be / pass-through-unshaped wan (single-archive aggregation).
    ('qos.class.bandwidth.tx.count', 38160, ['dscp:be', 'side:wan']),
    ('qos.class.bandwidth.tx.rate', 636.0, ['dscp:be', 'side:wan']),
    # DSCP peak: be / pass-through-unshaped wan.
    ('qos.class.bandwidth.tx.max', 636, ['dscp:be', 'side:wan']),
    # Shaper: traffic_class=2, qos_drops=0.
    ('qos.class.drops', 0, ['traffic_class:2', 'drop_type:qos']),
    ('qos.class.drop.percentage', 0, ['traffic_class:2']),
    # Probe: om_passThrough_9 (single-sample averages).
    ('circuit.sla.latency', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.loss', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.jitter', 60, ['probe_name:om_passThrough_9']),
    # Nexthop: om_passThrough_6 admin=60, oper=0.
    ('nexthop.status', 60, ['probe_name:om_passThrough_6', 'status_type:admin']),
    ('nexthop.status', 0, ['probe_name:om_passThrough_6', 'status_type:oper']),
]


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for metric_name, expected_count in EXPECTED_METRIC_COUNTS.items():
        aggregator.assert_metric(f'{NS}.{metric_name}', count=expected_count)

    for metric_name, expected_value, tag_subset in EXPECTED_VALUES:
        full_name = f'{NS}.{metric_name}'
        aggregator.assert_metric(full_name, value=expected_value)
        if tag_subset:
            aggregator.assert_metric_has_tags(full_name, tag_subset)

    aggregator.assert_all_metrics_covered()
