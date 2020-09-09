# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from packaging import version

from datadog_checks.dev import get_docker_hostname

PORT = '8500'

HOST = get_docker_hostname()

URL = 'http://{}:{}'.format(HOST, PORT)

CHECK_NAME = 'consul'

HERE = os.path.dirname(os.path.abspath(__file__))

CONSUL_VERSION = os.getenv('CONSUL_VERSION')

PROMETHEUS_ENDPOINT_AVAILABLE = version.parse(CONSUL_VERSION) > version.parse('1.1.0')

# Not all the metrics are exposed in this test environment.
PROMETHEUS_METRICS = [
    'consul.memberlist.gossip.count',
    'consul.memberlist.gossip.sum',
    'consul.memberlist.msg.alive',
    'consul.memberlist.probenode.count',
    'consul.memberlist.probenode.sum',
    'consul.memberlist.pushpullnode.count',
    'consul.memberlist.pushpullnode.sum',
    'consul.memberlist.tcp.accept',
    'consul.memberlist.tcp.connect',
    'consul.memberlist.tcp.sent',
    'consul.memberlist.udp.received',
    'consul.memberlist.udp.sent',
    'consul.raft.commitTime.count',
    'consul.raft.commitTime.sum',
    'consul.raft.leader.dispatchLog.count',
    'consul.raft.leader.dispatchLog.sum',
    'consul.raft.state.candidate',
    'consul.raft.state.leader',
    'consul.serf.coordinate.adjustment_ms.count',
    'consul.serf.coordinate.adjustment_ms.sum',
    'consul.serf.events',
    'consul.serf.member.join',
    'consul.serf.member.update',
    'consul.serf.msgs.received.count',
    'consul.serf.msgs.received.sum',
    'consul.serf.msgs.sent.count',
    'consul.serf.msgs.sent.sum',
]
