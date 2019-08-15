# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.zk import ZookeeperCheck

MNTR_METRICS = [
    'zookeeper.packets_sent',
    'zookeeper.approximate_data_size',
    'zookeeper.num_alive_connections',
    'zookeeper.open_file_descriptor_count',
    'zookeeper.avg_latency',
    'zookeeper.znode_count',
    'zookeeper.outstanding_requests',
    'zookeeper.min_latency',
    'zookeeper.ephemerals_count',
    'zookeeper.watch_count',
    'zookeeper.max_file_descriptor_count',
    'zookeeper.packets_received',
    'zookeeper.max_latency',
]

METRICS_34 = [
    'zookeeper.packets.sent',
    'zookeeper.latency.avg',
    'zookeeper.latency.min',
    'zookeeper.connections',
    'zookeeper.zxid.epoch',
    'zookeeper.bytes_sent',
    'zookeeper.bytes_received',
    'zookeeper.instances',
    'zookeeper.nodes',
    'zookeeper.zxid.count',
    'zookeeper.packets.received',
    'zookeeper.latency.max',
]


def assert_service_checks_ok(aggregator):
    aggregator.assert_service_check("zookeeper.ruok", status=ZookeeperCheck.OK)
    aggregator.assert_service_check("zookeeper.mode", status=ZookeeperCheck.OK)
