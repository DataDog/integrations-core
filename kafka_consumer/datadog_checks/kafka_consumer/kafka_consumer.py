# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
from collections import defaultdict
from time import time

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.kafka_consumer.client import KafkaClient
from datadog_checks.kafka_consumer.config import KafkaConfig
from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS, OFFSET_INVALID

MAX_TIMESTAMPS = 1000


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
            # Expected format: {(consumer_group, topic, partition): offset}
            consumer_offsets = self.get_consumer_offsets()
        except Exception:
            self.log.exception("There was a problem collecting consumer offsets from Kafka.")
            # don't raise because we might get valid broker offsets

        # Fetch the broker highwater offsets
        highwater_offsets = {}
        broker_timestamps = defaultdict(dict)
        cluster_id = ""
        persistent_cache_key = "broker_timestamps_"
        try:
            if len(consumer_offsets) < self._context_limit:
                # Fetch highwater offsets
                # Expected format: ({(topic, partition): offset}, cluster_id)
                highwater_offsets, cluster_id = self.get_highwater_offsets(consumer_offsets)
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

        total_contexts = len(consumer_offsets) + len(highwater_offsets)
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
        if self.config._close_admin_client:
            self.client.close_admin_client()

    def get_consumer_offsets(self):
        # {(consumer_group, topic, partition): offset}
        self.log.debug('Getting consumer offsets')
        consumer_offsets = {}

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

                if self.config._monitor_unlisted_consumer_groups or not self.config._consumer_groups_compiled_regex:
                    consumer_offsets[(consumer_group, topic, partition)] = offset
                else:
                    to_match = f"{consumer_group},{topic},{partition}"
                    if self.config._consumer_groups_compiled_regex.match(to_match):
                        consumer_offsets[(consumer_group, topic, partition)] = offset

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
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.items():
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
                consumer_group_state = self.get_consumer_group_state(consumer_group)
                consumer_group_tags.append(f'consumer_group_state:{consumer_group_state}')
            consumer_group_tags.extend(self.config._custom_tags)

            partitions = self.client.get_partitions_for_topic(topic)
            self.log.debug("Received partitions %s for topic %s", partitions, topic)
            if partitions is not None and partition in partitions:
                # report consumer offset if the partition is valid because even if leaderless the consumer offset will
                # be valid once the leader failover completes
                self.gauge('consumer_offset', consumer_offset, tags=consumer_group_tags)
                self.log.debug('%s consumer offset reported with %s tags', consumer_offset, consumer_group_tags)
                reported_contexts += 1

                if (topic, partition) not in highwater_offsets:
                    self.log.warning(
                        "Consumer group: %s has offsets for topic: %s partition: %s, but no stored highwater offset "
                        "(likely the partition is in the middle of leader failover) so cannot calculate consumer lag.",
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
                        "Consumer group: %s has offsets for topic: %s, partition: %s, but that topic has no partitions "
                        "in the cluster, so skipping reporting these offsets."
                    )
                else:
                    msg = (
                        "Consumer group: %s has offsets for topic: %s, partition: %s, but that topic partition isn't "
                        "included in the cluster partitions, so skipping reporting these offsets."
                    )
                self.log.warning(msg, consumer_group, topic, partition)
                self.client.request_metadata_update()  # force metadata update on next poll()
        self.log.debug('%s consumer offsets reported', reported_contexts)

    def get_consumer_group_state(self, consumer_group):
        consumer_group_state = ""
        # Get the consumer group state if present
        group_id, consumer_group_state = self.client.describe_consumer_groups(consumer_group)
        self.log.debug(
            "Consumer group: %s in state %s",
            group_id,
            consumer_group_state,
        )
        return consumer_group_state

    def get_highwater_offsets(self, consumer_offsets):
        self.log.debug('Getting highwater offsets')

        cluster_id = ""
        highwater_offsets = {}
        topics_with_consumer_offset = set()
        topic_partition_with_consumer_offset = set()

        if not self.config._monitor_all_broker_highwatermarks:
            for _, topic, partition in consumer_offsets:
                topics_with_consumer_offset.add(topic)
                topic_partition_with_consumer_offset.add((topic, partition))

        topic_partition_checked = set()

        for consumer_group, _topic, _partition in consumer_offsets:
            self.log.debug('CONSUMER GROUP: %s', consumer_group)
            if (_topic, _partition) in topic_partition_checked:
                self.log.debug('Highwater offset already collected for topic %s with partition %s', _topic, _partition)
                continue

            topic_partitions_for_highwater_offsets = set()

            self.client.open_consumer(consumer_group)
            cluster_id, topics = self.client.consumer_get_cluster_id_and_list_topics(consumer_group)

            for topic, partitions in topics:
                if topic in KAFKA_INTERNAL_TOPICS:
                    self.log.debug("Skipping internal topic %s", topic)
                    continue
                if not self.config._monitor_all_broker_highwatermarks and topic not in topics_with_consumer_offset:
                    self.log.debug("Skipping non-relevant topic %s", topic)
                    continue

                for partition in partitions:
                    if (
                        self.config._monitor_all_broker_highwatermarks
                        or (topic, partition) in topic_partition_with_consumer_offset
                    ):
                        topic_partitions_for_highwater_offsets.add((topic, partition))
                        self.log.debug('TOPIC: %s', topic)
                        self.log.debug('PARTITION: %s', partition)
                    else:
                        self.log.debug("Skipping non-relevant partition %s of topic %s", partition, topic)

            if len(topic_partitions_for_highwater_offsets) > 0:
                self.log.debug(
                    'Querying %s highwater offsets for consumer group %s',
                    len(topic_partitions_for_highwater_offsets),
                    consumer_group,
                )
                for topic, partition, offset in self.client.consumer_offsets_for_times(
                    partitions=topic_partitions_for_highwater_offsets
                ):
                    highwater_offsets[(topic, partition)] = offset
                    self.log.debug("Adding %s %s to checked set to facilitate early exit", topic, partition)
                    topic_partition_checked.add((topic, partition))
            else:
                self.log.debug('No new highwater offsets to query for consumer group %s', consumer_group)

            self.client.close_consumer()

        self.log.debug('Got %s highwater offsets', len(highwater_offsets))
        return highwater_offsets, cluster_id

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
