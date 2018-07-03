# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from datadog_checks.utils.common import get_docker_hostname

CHECK_NAME = 'zk'
HOST = get_docker_hostname()
PORT = 12181
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)
INSTANCE = {
    'host': HOST,
    'port': PORT,
    'expected_mode': "standalone",
    'tags': ["mytag"]
}

WRONG_EXPECTED_MODE = {
    'host': HOST,
    'port': PORT,
    'expected_mode': "follower",
    'tags': []
}

CONNECTION_FAILURE_CONFIG = {
    'host': HOST,
    'port': 2182,
    'expected_mode': "down",
    'tags': []
}

STAT_METRICS = [
    'zookeeper.latency.min',
    'zookeeper.latency.avg',
    'zookeeper.latency.max',
    'zookeeper.bytes_received',
    'zookeeper.bytes_sent',
    'zookeeper.connections',
    'zookeeper.connections',
    'zookeeper.bytes_outstanding',
    'zookeeper.outstanding_requests',
    'zookeeper.zxid.epoch',
    'zookeeper.zxid.count',
    'zookeeper.nodes',
    'zookeeper.instances',
    'zookeeper.packets.received',
    'zookeeper.packets.sent'
]

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

STATUS_TYPES = [
    'leader',
    'follower',
    'observer',
    'standalone',
    'down',
    'inactive',
    'unknown',
]
