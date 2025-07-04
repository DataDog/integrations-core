# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

from confluent_kafka import TopicPartition

SCHEMA_REGISTRY_MAGIC_BYTE = 0x00


def resolve_start_offsets(highwater_offsets, target_topic, target_partition, start_offset, n_messages):
    if int(target_partition) == -1:
        # in this case, we get n_messages, starting at offset latest - n_messages on each partition.
        # this doesn't match exactly to the latest messages, but if we don't do that, we could run into
        # edge cases when some partitions don't get any traffic.
        start_offsets = []
        for topic, partition in highwater_offsets:
            if topic == target_topic and highwater_offsets[(topic, partition)] >= 0:
                start_offsets.append(
                    TopicPartition(topic, partition, max(0, highwater_offsets[(topic, partition)] - n_messages + 1))
                )
                if len(start_offsets) >= n_messages:
                    break
        return start_offsets
    if int(start_offset) == -1:
        end_offset = highwater_offsets.get((target_topic, target_partition), -1)
        return (
            []
            if end_offset < 0
            else [TopicPartition(target_topic, target_partition, max(0, end_offset - n_messages + 1))]
        )
    return [TopicPartition(target_topic, target_partition, start_offset)]


def deserialize_message_maybe_schema_registry(message):
    try:
        return deserialize_message(message), None
    except Exception as e:
        # If the message is not a valid JSON, it might be a schema registry message, that is prefixed
        # with a magic byte and a schema ID.
        print(message)
        print(message[5:])
        if len(message) < 5 or message[0] != SCHEMA_REGISTRY_MAGIC_BYTE:
            raise e
        schema_id = int.from_bytes(message[1:5], 'big')
        message = message[5:]  # Skip the schema ID bytes
        return deserialize_message(message), schema_id


def deserialize_message(message):
    """Deserialize a message from Kafka. Supports JSON format.
    Args:
        message: Raw message bytes from Kafka
    Returns:
        Decoded message as a string
    """
    if len(message) == 0:
        return ""
    decoded = message.decode('utf-8')
    json.loads(decoded)
    return decoded
