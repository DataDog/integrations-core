# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .conftest import EXCLUDED_APPLIANCE_IP

NS = 'hpe_aruba_edgeconnect'

TUNNEL_AGGREGATE_ALIASES = ('all traffic', 'optimized traffic', 'pass-through', 'pass-through-unshaped')


EXPECTED_METRIC_COUNTS = {
    'orchestrator.reachability': 1,
    'device.reachability': 2,
    'device.uptime': 1,
    'device.cpu.usage': 4,
    'device.memory.usage': 1,
    'device.disk.usage': 5,
    'device.hardware.ok': 1,
    'interface.status': 2,
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
    'tunnel.throughput.tx.bytes.count': 58,
    'tunnel.throughput.rx.bytes.count': 58,
    'tunnel.throughput.tx.bytes.rate': 58,
    'tunnel.throughput.rx.bytes.rate': 58,
    'tunnel.throughput.tx.packets.count': 58,
    'tunnel.throughput.rx.packets.count': 58,
    'tunnel.throughput.tx.packets.rate': 58,
    'tunnel.throughput.rx.packets.rate': 58,
    'tunnel.throughput.tx.bytes.max': 58,
    'tunnel.throughput.rx.bytes.max': 58,
    'tunnel.throughput.tx.packets.max': 58,
    'tunnel.throughput.rx.packets.max': 58,
    'tunnel.latency': 29,
    'tunnel.latency.min': 29,
    'tunnel.latency.max': 29,
    'tunnel.loss': 58,
    'tunnel.jitter': 31,
    'tunnel.jitter.max': 31,
    'tunnel.qoe.mos': 62,
    'tunnel.qoe.mos.min': 62,
    'tunnel.availability': 29,
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
    'application.latency': 6,
}


EXPECTED_VALUES = [
    ('device.reachability', 1, []),
    ('device.uptime', 86400, []),
    ('device.cpu.usage', 30.0, ['cpu_state:user']),
    ('device.cpu.usage', 15.0, ['cpu_state:system']),
    ('device.cpu.usage', 3.0, ['cpu_state:irq']),
    ('device.cpu.usage', 2.0, ['cpu_state:nice']),
    ('device.memory.usage', (3174232 / 3945080) * 100.0, []),
    ('device.disk.usage', 21.0, ['mount:/']),
    ('device.disk.usage', 11.0, ['mount:/var']),
    ('device.hardware.ok', 1, []),
    ('interface.status', 1, ['interface_name:wan0', 'status_type:admin']),
    ('interface.status', 1, ['interface_name:wan0', 'status_type:oper']),
    ('interface.speed', 1000000000, ['interface_name:wan0']),
    ('interface.bandwidth.tx.count', 79920, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.tx.rate', 1332.0, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.rx.count', 41760, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.tx.max', 1332, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('interface.bandwidth.rx.max', 696, ['interface_name:wan0', 'traffic_type:pass-through-unshaped']),
    ('tunnel.latency', 1.39, ['tunnel_alias:to_NewYorkSP01_MPLS1-MPLS1']),
    ('tunnel.latency.min', 1.38, ['tunnel_alias:to_NewYorkSP01_MPLS1-MPLS1']),
    ('tunnel.jitter', 600, ['tunnel_name:bondedTunnel_16']),
    ('tunnel.jitter.max', 6, ['tunnel_name:bondedTunnel_16']),
    ('tunnel.qoe.mos', 4.0, ['tunnel_name:tunnel_12', 'fec:post']),
    ('tunnel.qoe.mos.min', 4.0, ['tunnel_name:tunnel_12', 'fec:post']),
    ('tunnel.internet_breakout.bandwidth.tx.count', 38160, ['interface_name:wan0']),
    ('tunnel.internet_breakout.bandwidth.tx.rate', 636.0, ['interface_name:wan0']),
    ('tunnel.internet_breakout.bandwidth.rx.max', 100000, ['interface_name:wan0']),
    ('qos.class.bandwidth.tx.count', 38160, ['dscp:be', 'side:wan']),
    ('qos.class.bandwidth.tx.rate', 636.0, ['dscp:be', 'side:wan']),
    ('qos.class.bandwidth.tx.max', 636, ['dscp:be', 'side:wan']),
    ('qos.class.drops', 0, ['overlay_name:BulkData', 'drop_type:qos']),
    ('qos.class.drop.percentage', 0, ['overlay_name:BulkData']),
    ('circuit.sla.latency', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.loss', 0, ['probe_name:om_passThrough_9']),
    ('circuit.sla.jitter', 60, ['probe_name:om_passThrough_9']),
    ('nexthop.status', 60, ['probe_name:om_passThrough_6', 'status_type:admin']),
    ('nexthop.status', 0, ['probe_name:om_passThrough_6', 'status_type:oper']),
    ('application.latency', 5.0, ['application:microsoft', 'tunnel_name:bondedTunnel_16', 'latency_type:cnd']),
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

    # The excluded appliance must not produce a device.reachability metric.
    for metric in aggregator.metrics(f'{NS}.device.reachability'):
        assert f'device_ip:{EXCLUDED_APPLIANCE_IP}' not in metric.tags

    aggregator.assert_all_metrics_covered()
