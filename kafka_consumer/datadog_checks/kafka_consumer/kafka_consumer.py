# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import heapq
import json
from collections import defaultdict
from time import time

from datadog_checks.base import AgentCheck
from datadog_checks.kafka_consumer.client import KafkaClient
from datadog_checks.kafka_consumer.cluster_metadata import ClusterMetadataCollector
from datadog_checks.kafka_consumer.config import KafkaConfig
from datadog_checks.kafka_consumer.connectors import KafkaConnectCollector
from datadog_checks.kafka_consumer.constants import (
    HIGH_WATERMARK,
    KAFKA_INTERNAL_TOPICS,
    OFFSET_INVALID,
)

MAX_TIMESTAMPS = 1000

LAG_EXTRAPOLATION_LIMIT_SECONDS = 600


class KafkaCheck(AgentCheck):
    __NAMESPACE__ = 'kafka'

    def __init__(self, name, init_config, instances):
        super(KafkaCheck, self).__init__(name, init_config, instances)
        self.config = KafkaConfig(self.init_config, self.instance, self.log)
        self._context_limit = self.config._context_limit
        self._data_streams_enabled = self.config._data_streams_enabled
        self._max_timestamps = int(self.instance.get('timestamp_history_size', MAX_TIMESTAMPS))
        self.client = KafkaClient(self.config, self.log)
        self.topic_partition_cache = {}
        self.check_initializations.insert(0, self.config.validate_config)

        # Initialize cluster metadata collector
        self.metadata_collector = ClusterMetadataCollector(self, self.client, self.config, self.log)
        # Eagerly constructed so the check object owns the collector's lifetime; collect() is a
        # no-op when _kafka_connect_urls is empty, so this is safe without a URL guard.
        self._connector_collector = KafkaConnectCollector(self, self.config, self.log)

    def check(self, _):
        """The main entrypoint of the check."""
        # Fetch Kafka consumer offsets

        consumer_offsets = {}

        try:
            self.client.request_metadata_update()
        except Exception as e:
            if self.config._cluster_monitoring_enabled:
                try:
                    self._send_cluster_monitoring_connection_error(str(e))
                except Exception:
                    self.log.warning("Failed to emit connection_error DSM event", exc_info=True)
            raise Exception(
                "Unable to connect to the AdminClient. This is likely due to an error in the configuration."
            ) from e

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
        low_watermark_offsets = {}
        topic_partitions = {}
        cluster_id = ""
        persistent_cache_key = "broker_timestamps_"
        consumer_contexts_count = self.count_consumer_contexts(consumer_offsets)
        try:
            # Cluster monitoring always requires highwater offsets (for topic.message_rate and other
            # cluster metadata metrics), so bypass the consumer context limit in that case.
            if consumer_contexts_count < self._context_limit or self.config._cluster_monitoring_enabled:
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
                highwater_offsets, cluster_id = self.get_highwater_offsets(partitions)
                if self.config._cluster_monitoring_enabled:
                    topic_partitions = self.client.get_topic_partitions()
                    low_watermark_offsets = self.metadata_collector.fetch_earliest_offsets(topic_partitions)
                if self._data_streams_enabled:
                    broker_timestamps = self._load_broker_timestamps(persistent_cache_key)
                    if low_watermark_offsets:
                        prune_floors = low_watermark_offsets
                    else:
                        self.log.debug("No low watermarks available; pruning cache by earliest consumer offset")
                        prune_floors = self._earliest_consumer_offsets(consumer_offsets)
                    self._add_broker_timestamps(broker_timestamps, highwater_offsets, prune_floors)
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
        # When cluster monitoring is enabled, all offsets and lag metrics are reported regardless
        # of context count so that the full cluster picture is always available.
        reporting_limit = float('inf') if self.config._cluster_monitoring_enabled else self._context_limit
        if total_contexts >= self._context_limit and not self.config._cluster_monitoring_enabled:
            self.warning(
                """Discovered %s metric contexts - this exceeds the maximum number of %s contexts permitted by the
                check. Please narrow your target by specifying in your kafka_consumer.yaml the consumer groups, topics
                and partitions you wish to monitor.""",
                total_contexts,
                self._context_limit,
            )

        self.config._auto_detected_cluster_id = cluster_id
        if self.config._kafka_cluster_id_override:
            cluster_id = self.config._kafka_cluster_id_override

        self.report_highwater_offsets(highwater_offsets, reporting_limit, cluster_id)
        self.report_consumer_offsets_and_lag(
            consumer_offsets,
            highwater_offsets,
            reporting_limit - len(highwater_offsets),
            broker_timestamps,
            cluster_id,
            low_watermark_offsets,
        )

        # Collect cluster metadata if enabled
        if self.config._cluster_monitoring_enabled:
            connect_status = self._collect_connect_status(cluster_id)
            self._send_cluster_monitoring_heartbeat(total_contexts, cluster_id, connect_status)

            try:
                self.metadata_collector.collect_all_metadata(highwater_offsets, low_watermark_offsets, topic_partitions)
            except Exception as e:
                self.log.error("Error collecting cluster metadata: %s", e)

        if self.config._close_admin_client:
            self.client.close_admin_client()

    def count_consumer_contexts(self, consumer_offsets):
        return sum(len(offsets) for offsets in consumer_offsets.values())

    def _get_broker_list(self) -> list[dict]:
        cluster_metadata = self.client._cluster_metadata
        if not (cluster_metadata and hasattr(cluster_metadata, 'brokers')):
            return []
        return [
            {'id': str(broker_meta.id), 'host': broker_meta.host, 'port': broker_meta.port}
            for broker_meta in cluster_metadata.brokers.values()
        ]

    def _emit_cluster_monitoring_event(self, payload: dict) -> None:
        payload.setdefault('collection_timestamp', int(time() * 1000))
        payload.setdefault('bootstrap_servers', self.config._kafka_connect_str)
        self.event_platform_event(json.dumps(payload), "data-streams-message")

    def _send_cluster_monitoring_connection_error(self, reason: str) -> None:
        self._emit_cluster_monitoring_event(
            {
                'kafka_cluster_id': self.config._kafka_cluster_id_override or '',
                'config_type': 'connection_error',
                'reason': reason,
            }
        )

    def _collect_connect_status(self, cluster_id: str) -> dict[str, bool] | None:
        """Collect connector status for all configured Connect endpoints, or None if unconfigured."""
        if not self.config._kafka_connect_urls:
            return None
        try:
            return self._connector_collector.collect(self.config._kafka_cluster_id_override or cluster_id)
        except Exception as e:
            self.log.error("Error collecting connector metadata: %s", e)
            return {}

    def _send_cluster_monitoring_heartbeat(
        self, total_contexts: int, cluster_id: str, connect_status: dict[str, bool] | None = None
    ) -> None:
        payload = {
            'kafka_cluster_id': cluster_id,
            'config_type': 'heartbeat',
            'contexts': total_contexts,
            'contexts_limit': self._context_limit,
            'brokers': self._get_broker_list(),
        }
        if self.config._kafka_cluster_id_override:
            payload['original_kafka_cluster_id'] = self.config._auto_detected_cluster_id
        if connect_status is not None:
            payload['connect_api_status'] = connect_status
        self._emit_cluster_monitoring_event(payload)

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

    def _earliest_consumer_offsets(self, consumer_offsets):
        """Return the lowest committed offset per (topic, partition) across all consumer groups."""
        earliest = {}
        for offsets in consumer_offsets.values():
            for topic_partition, offset in offsets.items():
                if topic_partition not in earliest or offset < earliest[topic_partition]:
                    earliest[topic_partition] = offset
        return earliest

    def _add_broker_timestamps(self, broker_timestamps, highwater_offsets, prune_floors=None):
        prune_floors = prune_floors or {}
        for (topic, partition), highwater_offset in highwater_offsets.items():
            timestamps = broker_timestamps["{}_{}".format(topic, partition)]
            # Reset detected: clear the whole cache. Low-offset survivors are from the
            # previous generation and VW pins the minimum endpoint, so they'd never age out.
            if any(o > highwater_offset for o in timestamps):
                timestamps.clear()
            timestamps[highwater_offset] = time()
            if len(timestamps) >= self._max_timestamps:
                prune_floor = prune_floors.get((topic, partition))
                if prune_floor is not None:
                    _prune_below_anchor(timestamps, prune_floor)
                _visvalingam_whyatt(timestamps, max(2, self._max_timestamps // 2))

    def _save_broker_timestamps(self, broker_timestamps, persistent_cache_key):
        """Saves broker timestamps to persistent cache."""
        self.write_persistent_cache(persistent_cache_key, json.dumps(broker_timestamps))

    def report_highwater_offsets(self, highwater_offsets, contexts_limit, cluster_id):
        """Report the broker highwater offsets."""
        reported_contexts = 0
        self.log.debug("Reporting broker offset metric")
        for (topic, partition), highwater_offset in highwater_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition, 'kafka_cluster_id:%s' % cluster_id]
            if self.config._kafka_cluster_id_override:
                broker_tags.append('original_kafka_cluster_id:%s' % self.config._auto_detected_cluster_id)
            broker_tags.extend(self.config._custom_tags)
            self.gauge('broker_offset', highwater_offset, tags=broker_tags)
            self.log.debug('%s highwater offset reported with %s tags', highwater_offset, broker_tags)
            reported_contexts += 1
            if reported_contexts == contexts_limit:
                return
        self.log.debug('%s highwater offsets reported', reported_contexts)

    def report_consumer_offsets_and_lag(
        self,
        consumer_offsets,
        highwater_offsets,
        contexts_limit,
        broker_timestamps,
        cluster_id,
        low_watermark_offsets=None,
    ):
        """Report the consumer offsets and consumer lag."""
        low_watermark_offsets = low_watermark_offsets or {}
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
                if self.config._kafka_cluster_id_override:
                    consumer_group_tags.append('original_kafka_cluster_id:%s' % self.config._auto_detected_cluster_id)
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
                        self.log.debug(
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
                        consumer_lag = 0

                    if reported_contexts < contexts_limit:
                        self.gauge('consumer_lag', consumer_lag, tags=consumer_group_tags)
                        self.log.debug('%s consumer lag reported with %s tags', consumer_lag, consumer_group_tags)
                        reported_contexts += 1

                    if not self._data_streams_enabled:
                        continue

                    timestamps = broker_timestamps["{}_{}".format(topic, partition)]
                    # The producer timestamp can be not set if there was an error fetching broker offsets.
                    producer_timestamp = timestamps.get(producer_offset, None)
                    low_watermark = low_watermark_offsets.get((topic, partition))
                    effective_offset = consumer_offset if low_watermark is None else max(consumer_offset, low_watermark)
                    consumer_timestamp = _get_interpolated_timestamp(timestamps, effective_offset)
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

    def get_highwater_offsets(self, partitions=None):
        self.log.debug('Getting highwater offsets')

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

        self.client.open_consumer(dd_consumer_group)
        try:
            cluster_id, _ = self.client.consumer_get_cluster_id_and_list_topics(dd_consumer_group)

            self.log.debug('Querying %s highwater offsets', len(topic_partitions_to_check))

            result = {}
            for topic, partition, offset in self.client.get_partition_offsets(
                partitions=topic_partitions_to_check, offset=HIGH_WATERMARK
            ):
                result[(topic, partition)] = offset
        finally:
            if self.config._close_admin_client:
                self.client.close_consumer()

        self.log.debug('Got %s highwater offsets', len(result))
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

    if offset < offset_before:
        # Cap how far past the oldest cached sample we extrapolate, so estimated lag stays bounded.
        timestamp = max(timestamp, timestamp_before - LAG_EXTRAPOLATION_LIMIT_SECONDS)
    return timestamp


def _prune_below_anchor(timestamps, floor):
    below = [o for o in timestamps if o < floor]
    if len(below) <= 1:
        return
    anchor = max(below)
    for o in below:
        if o != anchor:
            del timestamps[o]


def _visvalingam_whyatt(timestamps, target_count):
    if len(timestamps) <= target_count:
        return timestamps

    offsets = sorted(timestamps)
    prev = {o: (offsets[i - 1] if i > 0 else None) for i, o in enumerate(offsets)}
    nxt = {o: (offsets[i + 1] if i < len(offsets) - 1 else None) for i, o in enumerate(offsets)}
    alive = set(offsets)

    current = {}
    heap = []
    for o in offsets:
        if prev[o] is not None and nxt[o] is not None:
            current[o] = _interpolation_error(o, prev, nxt, timestamps)
            heap.append((current[o], o))
    heapq.heapify(heap)

    remaining = len(offsets)
    while remaining > target_count and heap:
        error, o = heapq.heappop(heap)
        if o not in alive or error != current.get(o):
            continue
        before, after = prev[o], nxt[o]
        alive.discard(o)
        del timestamps[o]
        remaining -= 1
        nxt[before], prev[after] = after, before
        for neighbor in (before, after):
            if prev[neighbor] is not None and nxt[neighbor] is not None:
                current[neighbor] = _interpolation_error(neighbor, prev, nxt, timestamps)
                heapq.heappush(heap, (current[neighbor], neighbor))
    return timestamps


def _interpolation_error(o, prev, nxt, timestamps):
    before, after = prev[o], nxt[o]
    predicted = timestamps[before] + (timestamps[after] - timestamps[before]) * (o - before) / (after - before)
    return abs(timestamps[o] - predicted)
