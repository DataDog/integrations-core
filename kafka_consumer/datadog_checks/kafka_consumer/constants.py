# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
DEFAULT_KAFKA_TIMEOUT = 5

CONTEXT_UPPER_BOUND = 500

# No sense fetching highwater offsets for internal topics
KAFKA_INTERNAL_TOPICS = {
    '__consumer_offsets',
    '__transaction_state',
    # _schema is a topic used by the Confluent registry
    '_schema',
    # confluent specific topics
    '_confluent_balancer_partition_samples',
    '_confluent_balancer_api_state',
    '_confluent_balancer_broker_samples',
    '_confluent-telemetry-metrics',
    '_confluent-command',
}

# https://github.com/confluentinc/confluent-kafka-python/issues/1329#issuecomment-1109627240
OFFSET_INVALID = -1001
