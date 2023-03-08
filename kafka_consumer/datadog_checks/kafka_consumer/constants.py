# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
DEFAULT_KAFKA_TIMEOUT = 5

CONTEXT_UPPER_BOUND = 500

# No sense fetching highwatever offsets for internal topics
KAFKA_INTERNAL_TOPICS = {
    '__consumer_offsets',
    '__transaction_state',
    '_schema',  # _schema is a topic used by the Confluent registry
}

BROKER_REQUESTS_BATCH_SIZE = 30

KRB5_CLIENT_KTNAME = 'KRB5_CLIENT_KTNAME'
