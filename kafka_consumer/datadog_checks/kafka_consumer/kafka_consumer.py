# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import base64
import json
from collections import defaultdict
from io import BytesIO
from time import time

from confluent_kafka import TopicPartition
from fastavro import schemaless_reader
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.json_format import MessageToJson
from google.protobuf.message import DecodeError, EncodeError

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.kafka_consumer.client import KafkaClient
from datadog_checks.kafka_consumer.cluster_metadata import ClusterMetadataCollector
from datadog_checks.kafka_consumer.config import KafkaConfig
from datadog_checks.kafka_consumer.constants import (
    HIGH_WATERMARK,
    KAFKA_INTERNAL_TOPICS,
    OFFSET_INVALID,
)

MAX_TIMESTAMPS = 1000
SCHEMA_REGISTRY_MAGIC_BYTE = 0x00
DATA_STREAMS_MESSAGES_CACHE_KEY = 'get_messages_cache'


class KafkaCheck(AgentCheck):
    __NAMESPACE__ = 'kafka'

    def __init__(self, name, init_config, instances):
        super(KafkaCheck, self).__init__(name, init_config, instances)
        self.config = KafkaConfig(self.init_config, self.instance, self.log)
        self._context_limit = self.config._context_limit
        self._data_streams_enabled = is_affirmative(self.instance.get('data_streams_enabled', False))
        self._max_timestamps = int(self.instance.get('timestamp_history_size', MAX_TIMESTAMPS))
        self.client = KafkaClient(self.config, self.log)
        self.topic_partition_cache = {}
        self.check_initializations.insert(0, self.config.validate_config)

        # Initialize cluster metadata collector
        self.metadata_collector = ClusterMetadataCollector(self, self.client, self.config, self.log)

    def check(self, _):
        """The main entrypoint of the check."""
        # Fetch Kafka consumer offsets

        consumer_offsets = {}

        try:
            self.client.request_metadata_update()
        except:
            raise Exception(
                "Unable to connect to the AdminClient. This is likely due to an error in the configuration."
            )

        try:
            # Fetch consumer offsets
            # Expected format: {consumer_group: {(topic, partition): offset}}
            consumer_offsets = self.get_consumer_offsets()
        except Exception:
            self.log.exception("There was a problem collecting consumer offsets from Kafka.")
            # don't raise because we might get valid broker offsets

        # Fetch the broker highwater offsets
        highwater_offsets = {}
        broker_timestamps = defaultdict(dict)
        cluster_id = ""
        persistent_cache_key = "broker_timestamps_"
        consumer_contexts_count = self.count_consumer_contexts(consumer_offsets)
        try:
            if consumer_contexts_count < self._context_limit:
                # Fetch highwater offsets
                # Build partitions list or use all if configured
                # If cluster monitoring is enabled, always fetch all broker highwater marks
                if self.config._cluster_monitoring_enabled or self.config._monitor_all_broker_highwatermarks:
                    partitions = None
                else:
                    partitions = set()
                    for _, offsets in consumer_offsets.items():
                        for topic, partition in offsets:
                            partitions.add((topic, partition))
                # Expected format: ({(topic, partition): offset}, cluster_id)
                highwater_offsets, cluster_id = self.get_watermark_offsets(partitions, mode=HIGH_WATERMARK)
                if self._data_streams_enabled:
                    broker_timestamps = self._load_broker_timestamps(persistent_cache_key)
                    self._add_broker_timestamps(broker_timestamps, highwater_offsets)
                    self._save_broker_timestamps(broker_timestamps, persistent_cache_key)
            else:
                self.warning("Context limit reached. Skipping highwater offset collection.")
        except Exception:
            self.log.exception("There was a problem collecting the highwater mark offsets.")
            # Unlike consumer offsets, fail immediately because we can't calculate consumer lag w/o highwater_offsets
            if self.config._close_admin_client:
                self.client.close_admin_client()
            raise

        total_contexts = consumer_contexts_count + len(highwater_offsets)
        self.log.debug(
            "Total contexts: %s, Consumer offsets: %s, Highwater offsets: %s",
            total_contexts,
            consumer_offsets,
            highwater_offsets,
        )
        if total_contexts >= self._context_limit:
            self.warning(
                """Discovered %s metric contexts - this exceeds the maximum number of %s contexts permitted by the
                check. Please narrow your target by specifying in your kafka_consumer.yaml the consumer groups, topics
                and partitions you wish to monitor.""",
                total_contexts,
                self._context_limit,
            )

        self.report_highwater_offsets(highwater_offsets, self._context_limit, cluster_id)
        self.report_consumer_offsets_and_lag(
            consumer_offsets,
            highwater_offsets,
            self._context_limit - len(highwater_offsets),
            broker_timestamps,
            cluster_id,
        )
        self.data_streams_live_message(highwater_offsets or {}, cluster_id)

        # Collect cluster metadata if enabled
        if self.config._cluster_monitoring_enabled:
            try:
                self.metadata_collector.collect_all_metadata(highwater_offsets)
            except Exception as e:
                self.log.error("Error collecting cluster metadata: %s", e)

        if self.config._close_admin_client:
            self.client.close_admin_client()

    def count_consumer_contexts(self, consumer_offsets):
        return sum(len(offsets) for offsets in consumer_offsets.values())

    def get_consumer_offsets(self):
        # {(consumer_group, topic, partition): offset}
        self.log.debug('Getting consumer offsets')
        consumer_offsets = defaultdict(dict)

        consumer_groups = self._get_consumer_groups()
        self.log.debug('Identified %s consumer groups', len(consumer_groups))

        offsets = self._get_offsets_for_groups(consumer_groups)
        self.log.debug('%s futures to be waited on', len(offsets))

        for consumer_group, topic_partitions in offsets:
            self.log.debug('RESULT CONSUMER GROUP: %s', consumer_group)

            for topic, partition, offset in topic_partitions:
                self.log.debug('RESULTS TOPIC: %s', topic)
                self.log.debug('RESULTS PARTITION: %s', partition)
                self.log.debug('RESULTS OFFSET: %s', offset)

                if offset == OFFSET_INVALID:
                    continue

                if (
                    self.config._monitor_unlisted_consumer_groups
                    or not self.config._consumer_groups_compiled_regex
                    or self.config._consumer_groups_compiled_regex.match(f"{consumer_group},{topic},{partition}")
                ):
                    consumer_offsets[consumer_group][(topic, partition)] = offset

        self.log.debug('Got %s consumer offsets', len(consumer_offsets))
        return consumer_offsets

    def _get_consumer_groups(self):
        # Get all consumer groups to monitor
        if self.config._monitor_unlisted_consumer_groups or self.config._consumer_groups_compiled_regex:
            return [grp for grp in self.client.list_consumer_groups() if grp]
        else:
            return self.config._consumer_groups

    def _get_offsets_for_groups(self, consumer_groups):
        groups = []

        # If either monitoring all consumer groups or regex, return all consumer group offsets (can filter later)
        if self.config._monitor_unlisted_consumer_groups or self.config._consumer_groups_compiled_regex:
            for consumer_group in consumer_groups:
                groups.append((consumer_group, None))
            return self.client.list_consumer_group_offsets(groups)

        for consumer_group in consumer_groups:
            # If topics are specified
            topics = consumer_groups.get(consumer_group)
            if not topics:
                groups.append((consumer_group, None))
                continue

            for topic, partitions in topics.items():
                if not partitions:
                    if topic in self.topic_partition_cache:
                        partitions = self.topic_partition_cache[topic]
                    else:
                        partitions = self.topic_partition_cache[topic] = self.client.get_partitions_for_topic(topic)
                topic_partitions = [(topic, p) for p in partitions]

                groups.append((consumer_group, topic_partitions))

        return self.client.list_consumer_group_offsets(groups)

    def _load_broker_timestamps(self, persistent_cache_key):
        """Loads broker timestamps from persistent cache."""
        broker_timestamps = defaultdict(dict)
        try:
            for topic_partition, content in json.loads(self.read_persistent_cache(persistent_cache_key)).items():
                for offset, timestamp in content.items():
                    broker_timestamps[topic_partition][int(offset)] = timestamp
        except Exception as e:
            self.log.warning('Could not read broker timestamps from cache: %s', str(e))
        return broker_timestamps

    def _messages_have_been_retrieved(self, config_id):
        """Check if messages have been retrieved for the given config ID."""
        try:
            content = self.read_persistent_cache(DATA_STREAMS_MESSAGES_CACHE_KEY)
            if content:
                config_ids = set(content.split(","))
                return config_id in config_ids
        except Exception as e:
            self.log.warning('Could not read persistent cache: %s', str(e))
        return False

    def _mark_messages_retrieved(self, config_id):
        """Mark that messages have been retrieved for the given config ID."""
        try:
            content = self.read_persistent_cache(DATA_STREAMS_MESSAGES_CACHE_KEY)
            if content:
                config_ids = set(content.split(","))
            else:
                config_ids = set()
            config_ids.add(config_id)
            self.write_persistent_cache(DATA_STREAMS_MESSAGES_CACHE_KEY, ",".join(config_ids))
        except Exception as e:
            self.log.warning('Could not write to persistent cache: %s', str(e))

    def _add_broker_timestamps(self, broker_timestamps, highwater_offsets):
        for (topic, partition), highwater_offset in highwater_offsets.items():
            timestamps = broker_timestamps["{}_{}".format(topic, partition)]
            timestamps[highwater_offset] = time()
            # If there's too many timestamps, we delete the oldest
            if len(timestamps) > self._max_timestamps:
                del timestamps[min(timestamps)]

    def _save_broker_timestamps(self, broker_timestamps, persistent_cache_key):
        """Saves broker timestamps to persistent cache."""
        self.write_persistent_cache(persistent_cache_key, json.dumps(broker_timestamps))

    def report_highwater_offsets(self, highwater_offsets, contexts_limit, cluster_id):
        """Report the broker highwater offsets."""
        reported_contexts = 0
        self.log.debug("Reporting broker offset metric")
        for (topic, partition), highwater_offset in highwater_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition, 'kafka_cluster_id:%s' % cluster_id]
            broker_tags.extend(self.config._custom_tags)
            self.gauge('broker_offset', highwater_offset, tags=broker_tags)
            self.log.debug('%s highwater offset reported with %s tags', highwater_offset, broker_tags)
            reported_contexts += 1
            if reported_contexts == contexts_limit:
                return
        self.log.debug('%s highwater offsets reported', reported_contexts)

    def report_consumer_offsets_and_lag(
        self, consumer_offsets, highwater_offsets, contexts_limit, broker_timestamps, cluster_id
    ):
        """Report the consumer offsets and consumer lag."""
        reported_contexts = 0
        self.log.debug("Reporting consumer offsets and lag metrics")
        for consumer_group, offsets in consumer_offsets.items():
            consumer_group_state = None
            for (topic, partition), consumer_offset in offsets.items():
                if reported_contexts >= contexts_limit:
                    self.log.debug(
                        "Reported contexts number %s greater than or equal to contexts limit of %s, returning",
                        str(reported_contexts),
                        str(contexts_limit),
                    )
                    self.log.debug('%s consumer offsets reported', reported_contexts)
                    return
                consumer_group_tags = [
                    'topic:%s' % topic,
                    'partition:%s' % partition,
                    'consumer_group:%s' % consumer_group,
                    'kafka_cluster_id:%s' % cluster_id,
                ]
                if self.config._collect_consumer_group_state:
                    if consumer_group_state is None:
                        consumer_group_state = self.get_consumer_group_state(consumer_group)
                    consumer_group_tags.append(f'consumer_group_state:{consumer_group_state}')
                consumer_group_tags.extend(self.config._custom_tags)

                partitions = self.client.get_partitions_for_topic(topic)
                self.log.debug("Received partitions %s for topic %s", partitions, topic)
                if partition in partitions:
                    # report consumer offset if the partition is valid because even if leaderless
                    # the consumer offset will be valid once the leader failover completes
                    self.gauge('consumer_offset', consumer_offset, tags=consumer_group_tags)
                    self.log.debug('%s consumer offset reported with %s tags', consumer_offset, consumer_group_tags)
                    reported_contexts += 1

                    if (topic, partition) not in highwater_offsets:
                        self.log.warning(
                            "Consumer group: %s has offsets for topic: %s partition: %s, "
                            "but no stored highwater offset (likely the partition is in the middle of leader failover) "
                            "so cannot calculate consumer lag.",
                            consumer_group,
                            topic,
                            partition,
                        )
                        continue
                    producer_offset = highwater_offsets[(topic, partition)]
                    consumer_lag = producer_offset - consumer_offset
                    if reported_contexts < contexts_limit:
                        self.gauge('consumer_lag', consumer_lag, tags=consumer_group_tags)
                        self.log.debug('%s consumer lag reported with %s tags', consumer_lag, consumer_group_tags)
                        reported_contexts += 1

                    if consumer_lag < 0:
                        # this will effectively result in data loss, so emit an event for max visibility
                        title = "Negative consumer lag for group: {}.".format(consumer_group)
                        message = (
                            "Consumer group: {}, topic: {}, partition: {} has negative consumer lag. This should never "
                            "happen and will result in the consumer skipping new messages until the lag turns "
                            "positive.".format(consumer_group, topic, partition)
                        )
                        key = "{}:{}:{}".format(consumer_group, topic, partition)
                        self.send_event(title, message, consumer_group_tags, 'consumer_lag', key, severity="error")
                        self.log.debug(message)

                    if not self._data_streams_enabled:
                        continue

                    timestamps = broker_timestamps["{}_{}".format(topic, partition)]
                    # The producer timestamp can be not set if there was an error fetching broker offsets.
                    producer_timestamp = timestamps.get(producer_offset, None)
                    consumer_timestamp = _get_interpolated_timestamp(timestamps, consumer_offset)
                    if consumer_timestamp is None or producer_timestamp is None:
                        continue
                    lag = producer_timestamp - consumer_timestamp
                    self.gauge('estimated_consumer_lag', lag, tags=consumer_group_tags)
                    reported_contexts += 1
                else:
                    if not partitions:
                        msg = (
                            "Consumer group: %s has offsets for topic: %s, partition: %s, "
                            "but that topic has no partitions in the cluster, "
                            "so skipping reporting these offsets."
                        )
                    else:
                        msg = (
                            "Consumer group: %s has offsets for topic: %s, partition: %s, "
                            "but that topic partition isn't included in the cluster partitions, "
                            "so skipping reporting these offsets."
                        )
                    self.log.warning(msg, consumer_group, topic, partition)
                    self.client.request_metadata_update()  # force metadata update on next poll()
        self.log.debug('%s consumer offsets reported', reported_contexts)

    def get_consumer_group_state(self, consumer_group):
        consumer_group_state = self.client.describe_consumer_group(consumer_group)
        self.log.debug(
            "Consumer group: %s is in state %s",
            consumer_group,
            consumer_group_state,
        )
        return consumer_group_state

    def get_watermark_offsets(self, partitions=None, mode=HIGH_WATERMARK):
        self.log.debug('Getting %s offsets', 'highwater' if mode == HIGH_WATERMARK else 'lowwater')

        # Build partitions set
        topic_partitions_to_check = set()
        if partitions is None:
            all_topic_partitions = self.client.get_topic_partitions()
            for topic in all_topic_partitions:
                if topic in KAFKA_INTERNAL_TOPICS:
                    self.log.debug("Skipping internal topic %s", topic)
                    continue
                for partition in all_topic_partitions[topic]:
                    topic_partitions_to_check.add((topic, partition))
        else:
            for topic, partition in partitions:
                if topic in KAFKA_INTERNAL_TOPICS:
                    self.log.debug("Skipping internal topic %s", topic)
                    continue
                topic_partitions_to_check.add((topic, partition))

        if not topic_partitions_to_check:
            self.log.debug('No partitions to check for offsets')
            return {}, ""

        dd_consumer_group = "datadog-agent"

        # Open consumer once for both cluster_id and offset fetching
        self.client.open_consumer(dd_consumer_group)
        cluster_id, _ = self.client.consumer_get_cluster_id_and_list_topics(dd_consumer_group)

        self.log.debug(
            'Querying %s %s offsets',
            len(topic_partitions_to_check),
            'highwater' if mode == HIGH_WATERMARK else 'lowwater',
        )

        result = {}
        for topic, partition, offset in self.client.consumer_offsets_for_times(
            partitions=topic_partitions_to_check, offset=mode
        ):
            result[(topic, partition)] = offset

        self.client.close_consumer()

        self.log.debug('Got %s %s offsets', len(result), 'highwater' if mode == HIGH_WATERMARK else 'lowwater')
        return result, cluster_id

    def send_event(self, title, text, tags, event_type, aggregation_key, severity='info'):
        """Emit an event to the Datadog Event Stream."""
        event_dict = {
            'timestamp': int(time()),
            'msg_title': title,
            'event_type': event_type,
            'alert_type': severity,
            'msg_text': text,
            'tags': tags,
            'aggregation_key': aggregation_key,
        }
        self.event(event_dict)

    def data_streams_live_message(self, highwater_offsets, cluster_id):
        monitored_topics = None
        for cfg in self.config.live_messages_configs:
            monitored_topics = monitored_topics or {topic.lower() for (topic, _) in highwater_offsets.keys()}
            kafka = cfg['kafka']
            topic = kafka["topic"]
            partition = kafka["partition"]
            start_offset = kafka["start_offset"]
            n_messages = kafka["n_messages"]
            cluster = kafka["cluster"]
            config_id = cfg["id"]
            value_format = kafka["value_format"]
            value_schema_str = kafka.get("value_schema", "")
            value_uses_schema_registry = kafka.get("value_uses_schema_registry", False)
            key_format = kafka["key_format"]
            key_schema_str = kafka.get("key_schema", "")
            key_uses_schema_registry = kafka.get("key_uses_schema_registry", False)
            if self._messages_have_been_retrieved(config_id):
                continue
            if not cluster or not cluster_id or cluster.lower() != cluster_id.lower():
                continue
            if topic.lower() not in monitored_topics:
                self.log.debug('Skipping live messages for topic %s because it is not monitored by this check', topic)
                continue
            start_offsets = resolve_start_offsets(highwater_offsets, topic, partition, start_offset, n_messages)

            if not start_offsets:
                self.log.warning('Unable to get a list of partitions to read from for live messages')
                self.send_log(
                    {
                        'timestamp': int(time()),
                        'config_id': config_id,
                        'technology': 'kafka',
                        'cluster': str(cluster),
                        'topic': str(topic),
                        'live_messages_error': 'Unable to list partitions to read from',
                        'message': "Unable to list partitions to read from",
                        'feature': 'data_streams_messages',
                    }
                )
                continue

            try:
                value_schema, key_schema = (
                    build_schema(value_format, value_schema_str),
                    build_schema(key_format, key_schema_str),
                )
            except (
                ValueError,
                json.JSONDecodeError,
                base64.binascii.Error,
                IndexError,
                KeyError,
                TypeError,
                DecodeError,
                EncodeError,
            ) as e:
                self.log.error(
                    "Failed to build schemas for config_id: %s, topic: %s, partition: %s. Error: %s",
                    config_id,
                    topic,
                    partition,
                    e,
                )
                continue

            consumer_group = f"datadog_messages_{config_id}"
            self.client.start_collecting_messages(start_offsets, consumer_group)
            try:
                for _ in range(n_messages):
                    message = self.client.get_next_message()
                    if message is None:
                        self.log.debug('Live messages: no message to retrieve')
                        self.send_log(
                            {
                                'timestamp': int(time()),
                                'config_id': config_id,
                                'technology': 'kafka',
                                'cluster': str(cluster),
                                'topic': str(topic),
                                'live_messages_error': 'No more messages to retrieve',
                                'message': "No more messages to retrieve",
                                'feature': 'data_streams_messages',
                            }
                        )
                        break
                    data = {
                        'timestamp': int(time()),
                        'technology': 'kafka',
                        'cluster': str(cluster),
                        'config_id': config_id,
                        'topic': str(topic),
                        'partition': str(message.partition()),
                        'offset': str(message.offset()),
                        'feature': 'data_streams_messages',
                    }
                    decoded_value, value_schema_id, decoded_key, key_schema_id = deserialize_message(
                        message,
                        value_format,
                        value_schema,
                        value_uses_schema_registry,
                        key_format,
                        key_schema,
                        key_uses_schema_registry,
                    )
                    if decoded_value:
                        data['message_value'] = decoded_value
                    else:
                        data['message'] = "Message format not supported"
                        data['live_messages_error'] = 'Message format not supported'
                    if value_schema_id:
                        data['value_schema_id'] = str(value_schema_id)
                    if decoded_key:
                        data['message_key'] = decoded_key
                    if key_schema_id:
                        data['key_schema_id'] = str(key_schema_id)
                    self.send_log(data)
            finally:
                self.client.close_consumer()
                self.client.delete_consumer_group(consumer_group)
            self._mark_messages_retrieved(config_id)


def _get_interpolated_timestamp(timestamps, offset):
    if offset in timestamps:
        return timestamps[offset]
    offsets = timestamps.keys()
    try:
        # Get the closest saved offsets to the consumer_offset
        offset_before = max([o for o in offsets if o < offset])
        offset_after = min([o for o in offsets if o > offset])
    except ValueError:
        if len(offsets) < 2:
            return None
        # We couldn't find offsets before and after the current consumer offset.
        # This happens when you start a consumer to replay data in the past:
        #   - We provision a consumer at t0 that will start consuming from t1 (t1 << t0).
        #   - It starts building a history of offset/timestamp pairs from the moment it started to run, i.e. t0.
        #   - So there is no offset/timestamp pair in the local history between t1 -> t0.
        # We'll take the min and max offsets available and assume the timestamp is an affine function
        # of the offset to compute an approximate broker timestamp corresponding to the current consumer offset.
        offset_before = min(offsets)
        offset_after = max(offsets)

    # We assume that the timestamp is an affine function of the offset
    timestamp_before = timestamps[offset_before]
    timestamp_after = timestamps[offset_after]
    slope = (timestamp_after - timestamp_before) / float(offset_after - offset_before)
    timestamp = slope * (offset - offset_after) + timestamp_after
    return timestamp


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


def deserialize_message(
    message,
    value_format,
    value_schema,
    value_uses_schema_registry,
    key_format,
    key_schema,
    key_uses_schema_registry,
):
    try:
        decoded_value, value_schema_id = _deserialize_bytes_maybe_schema_registry(
            message.value(), value_format, value_schema, value_uses_schema_registry
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None, None, None, None
    try:
        decoded_key, key_schema_id = _deserialize_bytes_maybe_schema_registry(
            message.key(), key_format, key_schema, key_uses_schema_registry
        )
        return decoded_value, value_schema_id, decoded_key, key_schema_id
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return decoded_value, value_schema_id, None, None


def _deserialize_bytes_maybe_schema_registry(message, message_format, schema, uses_schema_registry):
    if not message:
        return "", None
    if uses_schema_registry:
        # When explicitly configured, go straight to schema registry format
        if len(message) < 5 or message[0] != SCHEMA_REGISTRY_MAGIC_BYTE:
            msg_hex = message[:5].hex() if len(message) >= 5 else message.hex()
            raise ValueError(
                f"Expected schema registry format (magic byte 0x00 + 4-byte schema ID), "
                f"but message is too short or has wrong magic byte: {msg_hex}"
            )
        schema_id = int.from_bytes(message[1:5], 'big')
        message = message[5:]  # Skip the magic byte and schema ID bytes
        return _deserialize_bytes(message, message_format, schema), schema_id
    else:
        # Fallback behavior: try without schema registry format first, then with it
        try:
            return _deserialize_bytes(message, message_format, schema), None
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
            # If the message is not valid, it might be a schema registry message, that is prefixed
            # with a magic byte and a schema ID.
            if len(message) < 5 or message[0] != SCHEMA_REGISTRY_MAGIC_BYTE:
                raise e
            schema_id = int.from_bytes(message[1:5], 'big')
            message = message[5:]  # Skip the magic byte and schema ID bytes
            return _deserialize_bytes(message, message_format, schema), schema_id


def _deserialize_bytes(message, message_format, schema):
    """Deserialize a message from Kafka. Supports JSON format.
    Args:
        message: Raw message bytes from Kafka
    Returns:
        Decoded message as a string
    """
    if not message:
        return ""
    if message_format == 'protobuf':
        return _deserialize_protobuf(message, schema)
    elif message_format == 'avro':
        return _deserialize_avro(message, schema)
    else:
        return _deserialize_json(message)


def _deserialize_json(message):
    decoded = message.decode('utf-8')
    json.loads(decoded)
    return decoded


def _deserialize_protobuf(message, schema):
    """Deserialize a Protobuf message using google.protobuf with strict validation."""
    try:
        bytes_consumed = schema.ParseFromString(message)

        # Check if all bytes were consumed (strict validation)
        if bytes_consumed != len(message):
            raise ValueError(
                f"Not all bytes were consumed during Protobuf decoding! "
                f"Read {bytes_consumed} bytes, but message has {len(message)} bytes. "
            )

        return MessageToJson(schema)
    except Exception as e:
        raise ValueError(f"Failed to deserialize Protobuf message: {e}")


def _deserialize_avro(message, schema):
    """Deserialize an Avro message using fastavro with strict validation."""
    try:
        bio = BytesIO(message)
        initial_position = bio.tell()
        data = schemaless_reader(bio, schema)
        final_position = bio.tell()

        # Check if all bytes were consumed (strict validation)
        bytes_read = final_position - initial_position
        total_bytes = len(message)

        if bytes_read != total_bytes:
            raise ValueError(
                f"Not all bytes were consumed during Avro decoding! "
                f"Read {bytes_read} bytes, but message has {total_bytes} bytes. "
            )

        return json.dumps(data)
    except Exception as e:
        raise ValueError(f"Failed to deserialize Avro message: {e}")


def build_schema(message_format, schema_str):
    if message_format == 'protobuf':
        return build_protobuf_schema(schema_str)
    elif message_format == 'avro':
        return build_avro_schema(schema_str)
    return None


def build_avro_schema(schema_str):
    """Build an Avro schema from a JSON string."""
    schema = json.loads(schema_str)

    if schema is None:
        raise ValueError("Avro schema cannot be None")

    return schema


def build_protobuf_schema(schema_str):
    # schema is encoded in base64, decode it before passing it to ParseFromString
    schema_str = base64.b64decode(schema_str)
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.ParseFromString(schema_str)

    # Register all the file descriptors in a descriptor pool
    pool = descriptor_pool.DescriptorPool()
    for fd_proto in descriptor_set.file:
        pool.Add(fd_proto)

    # Pick the first message type from the first file descriptor
    first_fd = descriptor_set.file[0]
    # The file descriptor contains a list of message types (DescriptorProto)
    first_message_proto = first_fd.message_type[0]

    # The fully qualified name includes the package name + message name
    package = first_fd.package
    message_name = first_message_proto.name
    if package:
        full_name = f"{package}.{message_name}"
    else:
        full_name = message_name
    # # Get the message descriptor
    message_descriptor = pool.FindMessageTypeByName(full_name)
    # Create a dynamic message class
    schema = message_factory.GetMessageClass(message_descriptor)()

    if schema is None:
        raise ValueError("Protobuf schema cannot be None")

    return schema
