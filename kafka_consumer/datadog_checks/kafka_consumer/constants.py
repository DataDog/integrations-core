# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from kafka import errors as kafka_errors

# Kafka Errors
KAFKA_NO_ERROR = kafka_errors.NoError.errno
KAFKA_UNKNOWN_ERROR = kafka_errors.UnknownError.errno
KAFKA_UNKNOWN_TOPIC_OR_PARTITION = kafka_errors.UnknownTopicOrPartitionError.errno
KAFKA_NOT_LEADER_FOR_PARTITION = kafka_errors.NotLeaderForPartitionError.errno

DEFAULT_KAFKA_TIMEOUT = 5
DEFAULT_ZK_TIMEOUT = 5
DEFAULT_KAFKA_RETRIES = 3

CONTEXT_UPPER_BOUND = 200
