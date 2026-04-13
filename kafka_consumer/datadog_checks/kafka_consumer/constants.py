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

# Partition count above which cluster monitoring staggers offset collection across check runs
STAGGER_THRESHOLD = 10_000

# Default max consumer groups to track when monitoring all groups
DEFAULT_MAX_TRACKED_CONSUMER_GROUPS = 1_000

# Max total entries (groups × partitions) for consumer offset queries to keep response
# deserialization under ~6s (~157k entries/s)
MAX_CONSUMER_OFFSET_ENTRIES = 1_000_000

# Watermark query sentinels for batched offsets_for_times
HIGH_WATERMARK = -1  # latest offset
LOW_WATERMARK = 0  # earliest offset (timestamp 0)
