# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

COMMON_METRICS = [
    'rabbitmq.node.fd_used',
    'rabbitmq.node.disk_free',
    'rabbitmq.node.mem_used',
    'rabbitmq.node.run_queue',
    'rabbitmq.node.sockets_used',
    'rabbitmq.node.partitions',
    'rabbitmq.node.running',
    'rabbitmq.node.disk_alarm',
    'rabbitmq.node.mem_alarm',
]

E_METRICS = [
    'messages.confirm.count',
    'messages.confirm.rate',
    'messages.publish_in.count',
    'messages.publish_in.rate',
    'messages.publish_out.count',
    'messages.publish_out.rate',
    'messages.return_unroutable.count',
    'messages.return_unroutable.rate',
]

Q_METRICS = [
    'consumers',
    'bindings.count',
    'memory',
    'messages',
    'messages.rate',
    'messages_ready',
    'messages_ready.rate',
    'messages_unacknowledged',
    'messages_unacknowledged.rate',
    'messages.publish.count',
    'messages.publish.rate'
]
