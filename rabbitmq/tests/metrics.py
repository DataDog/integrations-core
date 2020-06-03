# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

COMMON_METRICS = [
    'rabbitmq.node.fd_used',
    'rabbitmq.node.disk_free',
    'rabbitmq.node.mem_used',
    'rabbitmq.node.mem_limit',
    'rabbitmq.node.run_queue',
    'rabbitmq.node.sockets_used',
    'rabbitmq.node.partitions',
    'rabbitmq.node.running',
    'rabbitmq.node.disk_alarm',
    'rabbitmq.node.mem_alarm',
]

E_METRICS = [
    'rabbitmq.exchange.messages.publish_in.count',
    'rabbitmq.exchange.messages.publish_in.rate',
    'rabbitmq.exchange.messages.publish_out.count',
    'rabbitmq.exchange.messages.publish_out.rate',
]

# Only present in 3.5
E_METRICS_35 = [
    'rabbitmq.exchange.messages.confirm.count',
    'rabbitmq.exchange.messages.confirm.rate',
    'rabbitmq.exchange.messages.return_unroutable.count',
    'rabbitmq.exchange.messages.return_unroutable.rate',
]

Q_METRICS = [
    'rabbitmq.queue.consumers',
    'rabbitmq.queue.bindings.count',
    'rabbitmq.queue.memory',
    'rabbitmq.queue.messages',
    'rabbitmq.queue.messages.rate',
    'rabbitmq.queue.messages_ready',
    'rabbitmq.queue.messages_ready.rate',
    'rabbitmq.queue.messages_unacknowledged',
    'rabbitmq.queue.messages_unacknowledged.rate',
    'rabbitmq.queue.messages.publish.count',
    'rabbitmq.queue.messages.publish.rate',
]

# Present from 3.6
Q_METRICS_36 = [
    'rabbitmq.queue.head_message_timestamp',
]

OVERVIEW_METRICS_TOTALS = [
    'rabbitmq.overview.object_totals.connections',
    'rabbitmq.overview.object_totals.channels',
    'rabbitmq.overview.object_totals.queues',
    'rabbitmq.overview.object_totals.consumers',
    'rabbitmq.overview.queue_totals.messages.count',
    'rabbitmq.overview.queue_totals.messages.rate',
    'rabbitmq.overview.queue_totals.messages_ready.count',
    'rabbitmq.overview.queue_totals.messages_ready.rate',
    'rabbitmq.overview.queue_totals.messages_unacknowledged.count',
    'rabbitmq.overview.queue_totals.messages_unacknowledged.rate',
]

OVERVIEW_METRICS_MESSAGES = [
    'rabbitmq.overview.messages.ack.count',
    'rabbitmq.overview.messages.ack.rate',
    'rabbitmq.overview.messages.confirm.count',
    'rabbitmq.overview.messages.confirm.rate',
    'rabbitmq.overview.messages.deliver_get.count',
    'rabbitmq.overview.messages.deliver_get.rate',
    'rabbitmq.overview.messages.publish.count',
    'rabbitmq.overview.messages.publish.rate',
    'rabbitmq.overview.messages.publish_in.count',
    'rabbitmq.overview.messages.publish_in.rate',
    'rabbitmq.overview.messages.publish_out.count',
    'rabbitmq.overview.messages.publish_out.rate',
    'rabbitmq.overview.messages.return_unroutable.count',
    'rabbitmq.overview.messages.return_unroutable.rate',
    'rabbitmq.overview.messages.redeliver.count',
    'rabbitmq.overview.messages.redeliver.rate',
]
