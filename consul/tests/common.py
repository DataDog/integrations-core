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
    'consul.memberlist.msg.alive',
    'consul.memberlist.tcp.accept',
    'consul.memberlist.tcp.connect',
    'consul.memberlist.tcp.sent',
    'consul.memberlist.udp.received',
    'consul.memberlist.udp.sent',
    'consul.raft.state.candidate',
    'consul.raft.state.leader',
    'consul.serf.events',
    'consul.serf.member.join',
    'consul.serf.member.update',
    'consul.raft.leader.lastContact.count',
]

PROMETHEUS_HIST_METRICS = [
    'consul.memberlist.gossip.',
    'consul.memberlist.probenode.',
    'consul.memberlist.probenode.',
    'consul.memberlist.pushpullnode.',
    'consul.raft.commitTime.',
    'consul.raft.leader.dispatchLog.',
    'consul.raft.replication.appendEntries.rpc.',
    'consul.raft.replication.heartbeat.',
    'consul.serf.coordinate.adjustment_ms.',
    'consul.serf.msgs.sent.',
    'consul.serf.msgs.received.',
]
