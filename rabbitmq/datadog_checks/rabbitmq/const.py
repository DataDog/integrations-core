# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

EVENT_TYPE = SOURCE_TYPE_NAME = 'rabbitmq'
EXCHANGE_TYPE = 'exchanges'
QUEUE_TYPE = 'queues'
NODE_TYPE = 'nodes'
CONNECTION_TYPE = 'connections'
OVERVIEW_TYPE = 'overview'
MAX_DETAILED_EXCHANGES = 50
MAX_DETAILED_QUEUES = 200
MAX_DETAILED_NODES = 100
# Post an event in the stream when the number of queues or nodes to
# collect is above 90% of the limit:
ALERT_THRESHOLD = 0.9
EXCHANGE_ATTRIBUTES = [
    # Path, Name, Operation
    ('message_stats/ack', 'messages.ack.count', float),
    ('message_stats/ack_details/rate', 'messages.ack.rate', float),
    ('message_stats/confirm', 'messages.confirm.count', float),
    ('message_stats/confirm_details/rate', 'messages.confirm.rate', float),
    ('message_stats/deliver_get', 'messages.deliver_get.count', float),
    ('message_stats/deliver_get_details/rate', 'messages.deliver_get.rate', float),
    ('message_stats/publish', 'messages.publish.count', float),
    ('message_stats/publish_details/rate', 'messages.publish.rate', float),
    ('message_stats/publish_in', 'messages.publish_in.count', float),
    ('message_stats/publish_in_details/rate', 'messages.publish_in.rate', float),
    ('message_stats/publish_out', 'messages.publish_out.count', float),
    ('message_stats/publish_out_details/rate', 'messages.publish_out.rate', float),
    ('message_stats/return_unroutable', 'messages.return_unroutable.count', float),
    ('message_stats/return_unroutable_details/rate', 'messages.return_unroutable.rate', float),
    ('message_stats/redeliver', 'messages.redeliver.count', float),
    ('message_stats/redeliver_details/rate', 'messages.redeliver.rate', float),
]
QUEUE_ATTRIBUTES = [
    # Path, Name, Operation
    ('active_consumers', 'active_consumers', float),
    ('consumers', 'consumers', float),
    ('consumer_utilisation', 'consumer_utilisation', float),
    ('head_message_timestamp', 'head_message_timestamp', int),
    ('memory', 'memory', float),
    ('messages', 'messages', float),
    ('messages_details/rate', 'messages.rate', float),
    ('messages_ready', 'messages_ready', float),
    ('messages_ready_details/rate', 'messages_ready.rate', float),
    ('message_bytes', 'message_bytes', float),
    ('messages_unacknowledged', 'messages_unacknowledged', float),
    ('messages_unacknowledged_details/rate', 'messages_unacknowledged.rate', float),
    ('message_stats/ack', 'messages.ack.count', float),
    ('message_stats/ack_details/rate', 'messages.ack.rate', float),
    ('message_stats/deliver', 'messages.deliver.count', float),
    ('message_stats/deliver_details/rate', 'messages.deliver.rate', float),
    ('message_stats/deliver_get', 'messages.deliver_get.count', float),
    ('message_stats/deliver_get_details/rate', 'messages.deliver_get.rate', float),
    ('message_stats/publish', 'messages.publish.count', float),
    ('message_stats/publish_details/rate', 'messages.publish.rate', float),
    ('message_stats/redeliver', 'messages.redeliver.count', float),
    ('message_stats/redeliver_details/rate', 'messages.redeliver.rate', float),
]

NODE_ATTRIBUTES = [
    ('fd_used', 'fd_used', float),
    ('disk_free', 'disk_free', float),
    ('mem_used', 'mem_used', float),
    ('mem_limit', 'mem_limit', float),
    ('run_queue', 'run_queue', float),
    ('sockets_used', 'sockets_used', float),
    ('partitions', 'partitions', len),
    ('running', 'running', float),
    ('mem_alarm', 'mem_alarm', float),
    ('disk_free_alarm', 'disk_alarm', float),
]

OVERVIEW_ATTRIBUTES = [
    ("object_totals/connections", "object_totals.connections", float),
    ("object_totals/channels", "object_totals.channels", float),
    ("object_totals/queues", "object_totals.queues", float),
    ("object_totals/consumers", "object_totals.consumers", float),
    ("queue_totals/messages", "queue_totals.messages.count", float),
    ("queue_totals/messages_details/rate", "queue_totals.messages.rate", float),
    ("queue_totals/messages_ready", "queue_totals.messages_ready.count", float),
    ("queue_totals/messages_ready_details/rate", "queue_totals.messages_ready.rate", float),
    ("queue_totals/messages_unacknowledged", "queue_totals.messages_unacknowledged.count", float),
    ("queue_totals/messages_unacknowledged_details/rate", "queue_totals.messages_unacknowledged.rate", float),
    ('message_stats/ack', 'messages.ack.count', float),
    ('message_stats/ack_details/rate', 'messages.ack.rate', float),
    ('message_stats/confirm', 'messages.confirm.count', float),
    ('message_stats/confirm_details/rate', 'messages.confirm.rate', float),
    ('message_stats/deliver_get', 'messages.deliver_get.count', float),
    ('message_stats/deliver_get_details/rate', 'messages.deliver_get.rate', float),
    ('message_stats/publish', 'messages.publish.count', float),
    ('message_stats/publish_details/rate', 'messages.publish.rate', float),
    ('message_stats/publish_in', 'messages.publish_in.count', float),
    ('message_stats/publish_in_details/rate', 'messages.publish_in.rate', float),
    ('message_stats/publish_out', 'messages.publish_out.count', float),
    ('message_stats/publish_out_details/rate', 'messages.publish_out.rate', float),
    ('message_stats/drop_unroutable', 'messages.drop_unroutable.count', float),
    ('message_stats/drop_unroutable_details/rate', 'messages.drop_unroutable.rate', float),
    ('message_stats/return_unroutable', 'messages.return_unroutable.count', float),
    ('message_stats/return_unroutable_details/rate', 'messages.return_unroutable.rate', float),
    ('message_stats/redeliver', 'messages.redeliver.count', float),
    ('message_stats/redeliver_details/rate', 'messages.redeliver.rate', float),
]

ATTRIBUTES = {
    EXCHANGE_TYPE: EXCHANGE_ATTRIBUTES,
    QUEUE_TYPE: QUEUE_ATTRIBUTES,
    NODE_TYPE: NODE_ATTRIBUTES,
    OVERVIEW_TYPE: OVERVIEW_ATTRIBUTES,
}

TAG_PREFIX = 'rabbitmq'
TAGS_MAP = {
    EXCHANGE_TYPE: {'name': 'exchange', 'vhost': 'vhost', 'exchange_family': 'exchange_family'},
    QUEUE_TYPE: {'node': 'node', 'name': 'queue', 'vhost': 'vhost', 'policy': 'policy', 'queue_family': 'queue_family'},
    NODE_TYPE: {'name': 'node'},
    OVERVIEW_TYPE: {'cluster_name': 'cluster'},
}

METRIC_SUFFIX = {EXCHANGE_TYPE: "exchange", QUEUE_TYPE: "queue", NODE_TYPE: "node", OVERVIEW_TYPE: "overview"}


class RabbitMQException(Exception):
    pass
