# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
from collections import defaultdict
from time import time

from kafka import errors as kafka_errors
from kafka.protocol.offset import OffsetRequest, OffsetResetStrategy, OffsetResponse
from kafka.structs import TopicPartition

from datadog_checks.base import AgentCheck, ConfigurationError

from .constants import BROKER_REQUESTS_BATCH_SIZE, KAFKA_INTERNAL_TOPICS

MAX_TIMESTAMPS = 1000


class NewKafkaConsumerCheck(object):
    """
    Check the offsets and lag of Kafka consumers. This check also returns broker highwater offsets.

    For details about the supported options, see the associated `conf.yaml.example`.
    """

    def __init__(self, parent_check):
        self._parent_check = parent_check
        self._broker_requests_batch_size = self.instance.get('broker_requests_batch_size', BROKER_REQUESTS_BATCH_SIZE)
        self._kafka_client = None
        self._broker_timestamp_cache_key = 'broker_timestamps' + "".join(sorted(self._custom_tags))

    def __getattr__(self, item):
        try:
            return getattr(self._parent_check, item)
        except AttributeError:
            raise AttributeError("NewKafkaConsumerCheck has no attribute called {}".format(item))

    @property
    def kafka_client(self):
        if self._kafka_client is None:
            # if `kafka_client_api_version` is not set, then kafka-python automatically probes the cluster for
            # broker version during the bootstrapping process. Note that this returns the first version found, so in
            # a mixed-version cluster this will be a non-deterministic result.
            kafka_version = self.instance.get('kafka_client_api_version')
            if isinstance(kafka_version, str):
                kafka_version = tuple(map(int, kafka_version.split(".")))

            self._kafka_client = self._create_kafka_admin_client(api_version=kafka_version)
        return self._kafka_client

    def check(self):
        """The main entrypoint of the check."""
        self._consumer_offsets = {}  # Expected format: {(consumer_group, topic, partition): offset}
        self._highwater_offsets = {}  # Expected format: {(topic, partition): offset}

        # For calculating consumer lag, we have to fetch both the consumer offset and the broker highwater offset.
        # There's a potential race condition because whichever one we check first may be outdated by the time we check
        # the other. Better to check consumer offsets before checking broker offsets because worst case is that
        # overstates consumer lag a little. Doing it the other way can understate consumer lag to the point of having
        # negative consumer lag, which just creates confusion because it's theoretically impossible.

        # Fetch Kafka consumer offsets
        try:
            self._get_consumer_offsets()
        except Exception:
            self.log.exception("There was a problem collecting consumer offsets from Kafka.")
            # don't raise because we might get valid broker offsets

        self._load_broker_timestamps()
        # Fetch the broker highwater offsets
        try:
            if len(self._consumer_offsets) < self._context_limit:
                self._get_highwater_offsets()
            else:
                self.warning("Context limit reached. Skipping highwater offset collection.")
        except Exception:
            self.log.exception("There was a problem collecting the highwater mark offsets.")
            # Unlike consumer offsets, fail immediately because we can't calculate consumer lag w/o highwater_offsets
            raise

        total_contexts = len(self._consumer_offsets) + len(self._highwater_offsets)
        if total_contexts >= self._context_limit:
            self.warning(
                """Discovered %s metric contexts - this exceeds the maximum number of %s contexts permitted by the
                check. Please narrow your target by specifying in your kafka_consumer.yaml the consumer groups, topics
                and partitions you wish to monitor.""",
                total_contexts,
                self._context_limit,
            )

        self._save_broker_timestamps()

        # Report the metrics
        self._report_highwater_offsets(self._context_limit)
        self._report_consumer_offsets_and_lag(self._context_limit - len(self._highwater_offsets))

        self._collect_broker_metadata()

    def _load_broker_timestamps(self):
        """Loads broker timestamps from persistent cache."""
        self._broker_timestamps = defaultdict(dict)
        try:
            json_cache = self._read_persistent_cache()
            for topic_partition, content in json.loads(json_cache).items():
                for offset, timestamp in content.items():
                    self._broker_timestamps[topic_partition][int(offset)] = timestamp
        except Exception as e:
            self.log.warning('Could not read broker timestamps from cache: %s', str(e))

    def _read_persistent_cache(self):
        return self._parent_check.read_persistent_cache(self._broker_timestamp_cache_key)

    def _save_broker_timestamps(self):
        self._parent_check.write_persistent_cache(self._broker_timestamp_cache_key, json.dumps(self._broker_timestamps))

    def _create_kafka_admin_client(self, api_version):
        """Return a KafkaAdminClient."""
        # TODO accept None (which inherits kafka-python default of localhost:9092)
        kafka_admin_client = self.create_kafka_admin_client()
        self.log.debug("KafkaAdminClient api_version: %s", kafka_admin_client.config['api_version'])
        # Force initial population of the local cluster metadata cache
        kafka_admin_client._client.poll(future=kafka_admin_client._client.cluster.request_update())
        if kafka_admin_client._client.cluster.topics(exclude_internal_topics=False) is None:
            raise RuntimeError("Local cluster metadata cache did not populate.")
        return kafka_admin_client

    def _get_highwater_offsets(self):
        """Fetch highwater offsets for topic_partitions in the Kafka cluster.

        Do this for all partitions in the cluster because even if it has no consumers, we may want to measure whether
        producers are successfully producing.

        If monitor_all_broker_highwatermarks is True, will fetch for all partitions in the cluster. Otherwise highwater
        mark offsets will only be fetched for topic partitions where this check run has already fetched a consumer
        offset.

        Internal Kafka topics like __consumer_offsets, __transaction_state, etc are always excluded.

        Any partitions that don't currently have a leader will be skipped.

        Sends one OffsetRequest per broker to get offsets for all partitions where that broker is the leader:
        https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetAPI(AKAListOffset)

        For speed, all the brokers are queried in parallel using callbacks. The callback flow is:
            1. Issue an OffsetRequest to every broker
            2. Attach a callback to each OffsetResponse that parses the response and saves the highwater offsets.
        """
        highwater_futures = []  # No need to store on object because the callbacks don't create additional futures

        # If we aren't fetching all broker highwater offsets, then construct the unique set of topic partitions for
        # which this run of the check has at least once saved consumer offset. This is later used as a filter for
        # excluding partitions.
        if not self._monitor_all_broker_highwatermarks:
            tps_with_consumer_offset = {(topic, partition) for (_, topic, partition) in self._consumer_offsets}

        for batch in self.batchify(self.kafka_client._client.cluster.brokers(), self._broker_requests_batch_size):
            for broker in batch:
                broker_led_partitions = self.kafka_client._client.cluster.partitions_for_broker(broker.nodeId)
                if broker_led_partitions is None:
                    continue

                # Take the partitions for which this broker is the leader and group them by topic in order to construct
                # the OffsetRequest while simultaneously filtering out partitions we want to exclude
                partitions_grouped_by_topic = defaultdict(list)
                for topic, partition in broker_led_partitions:
                    # No sense fetching highwater offsets for internal topics
                    if topic not in KAFKA_INTERNAL_TOPICS and (
                        self._monitor_all_broker_highwatermarks or (topic, partition) in tps_with_consumer_offset
                    ):
                        partitions_grouped_by_topic[topic].append(partition)

                # Construct the OffsetRequest
                max_offsets = 1
                request = OffsetRequest[0](
                    replica_id=-1,
                    topics=[
                        (topic, [(partition, OffsetResetStrategy.LATEST, max_offsets) for partition in partitions])
                        for topic, partitions in partitions_grouped_by_topic.items()
                    ],
                )

                highwater_future = self.kafka_client._send_request_to_node(node_id=broker.nodeId, request=request)
                highwater_future.add_callback(self._highwater_offsets_callback)
                highwater_futures.append(highwater_future)

            # Loop until all futures resolved.
            self.kafka_client._wait_for_futures(highwater_futures)

    def _highwater_offsets_callback(self, response):
        """Callback that parses an OffsetFetchResponse and saves it to the highwater_offsets dict."""
        if type(response) not in OffsetResponse:
            raise RuntimeError("response type should be OffsetResponse, but instead was %s." % type(response))
        for topic, partitions_data in response.topics:
            for partition, error_code, offsets in partitions_data:
                error_type = kafka_errors.for_code(error_code)
                if error_type is kafka_errors.NoError:
                    self._highwater_offsets[(topic, partition)] = offsets[0]
                    timestamps = self._broker_timestamps["{}_{}".format(topic, partition)]
                    timestamps[offsets[0]] = time()
                    # If there's too many timestamps, we delete the oldest
                    if len(timestamps) > MAX_TIMESTAMPS:
                        del timestamps[min(timestamps)]
                elif error_type is kafka_errors.NotLeaderForPartitionError:
                    self.log.warning(
                        "Kafka broker returned %s (error_code %s) for topic %s, partition: %s. This should only happen "
                        "if the broker that was the partition leader when kafka_admin_client last fetched metadata is "
                        "no longer the leader.",
                        error_type.message,
                        error_type.errno,
                        topic,
                        partition,
                    )
                    self.kafka_client._client.cluster.request_update()  # force metadata update on next poll()
                elif error_type is kafka_errors.UnknownTopicOrPartitionError:
                    self.log.warning(
                        "Kafka broker returned %s (error_code %s) for topic: %s, partition: %s. This should only "
                        "happen if the topic is currently being deleted or the check configuration lists non-existent "
                        "topic partitions.",
                        error_type.message,
                        error_type.errno,
                        topic,
                        partition,
                    )
                else:
                    raise error_type(
                        "Unexpected error encountered while attempting to fetch the highwater offsets for topic: %s, "
                        "partition: %s." % (topic, partition)
                    )

    def _report_highwater_offsets(self, contexts_limit):
        """Report the broker highwater offsets."""
        reported_contexts = 0
        for (topic, partition), highwater_offset in self._highwater_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            broker_tags.extend(self._custom_tags)
            self.gauge('broker_offset', highwater_offset, tags=broker_tags)
            reported_contexts += 1
            if reported_contexts == contexts_limit:
                return

    def _report_consumer_offsets_and_lag(self, contexts_limit):
        """Report the consumer offsets and consumer lag."""
        reported_contexts = 0
        for (consumer_group, topic, partition), consumer_offset in self._consumer_offsets.items():
            if reported_contexts >= contexts_limit:
                return
            consumer_group_tags = ['topic:%s' % topic, 'partition:%s' % partition, 'consumer_group:%s' % consumer_group]
            consumer_group_tags.extend(self._custom_tags)

            partitions = self.kafka_client._client.cluster.partitions_for_topic(topic)
            if partitions is not None and partition in partitions:
                # report consumer offset if the partition is valid because even if leaderless the consumer offset will
                # be valid once the leader failover completes
                self.gauge('consumer_offset', consumer_offset, tags=consumer_group_tags)
                reported_contexts += 1

                if (topic, partition) not in self._highwater_offsets:
                    self.log.warning(
                        "Consumer group: %s has offsets for topic: %s partition: %s, but no stored highwater offset "
                        "(likely the partition is in the middle of leader failover) so cannot calculate consumer lag.",
                        consumer_group,
                        topic,
                        partition,
                    )
                    continue
                producer_offset = self._highwater_offsets[(topic, partition)]
                consumer_lag = producer_offset - consumer_offset
                if reported_contexts < contexts_limit:
                    self.gauge('consumer_lag', consumer_lag, tags=consumer_group_tags)
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

                if reported_contexts >= contexts_limit:
                    continue
                timestamps = self._broker_timestamps["{}_{}".format(topic, partition)]
                # producer_timestamp is set in the same check, so it should never be None
                producer_timestamp = timestamps[producer_offset]
                consumer_timestamp = self._get_interpolated_timestamp(timestamps, consumer_offset)
                if consumer_timestamp is None or producer_timestamp is None:
                    continue
                lag = producer_timestamp - consumer_timestamp
                self.gauge('consumer_lag_seconds', lag, tags=consumer_group_tags)
                reported_contexts += 1
            else:
                if partitions is None:
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
                self.kafka_client._client.cluster.request_update()  # force metadata update on next poll()

    def _get_interpolated_timestamp(self, timestamps, offset):
        if offset in timestamps:
            return timestamps[offset]
        offsets = timestamps.keys()
        try:
            # Get the most close saved offsets to the consumer_offset
            offset_before = max([o for o in offsets if o < offset])
            offset_after = min([o for o in offsets if o > offset])
        except ValueError:
            if len(offsets) < 2:
                self.log.debug("Can't compute the timestamp as we don't have enough offsets history yet")
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

    def _get_consumer_offsets(self):
        """Fetch Consumer Group offsets from Kafka.

        Also fetch consumer_groups, topics, and partitions if not already specified.

        For speed, all the brokers are queried in parallel using callbacks.
        The callback flow is:
            A: When fetching all groups ('monitor_unlisted_consumer_groups' is True):
                1. Issue a ListGroupsRequest to every broker
                2. Attach a callback to each ListGroupsRequest that issues OffsetFetchRequests for every group.
                   Note: Because a broker only returns groups for which it is the coordinator, as an optimization we
                   skip the FindCoordinatorRequest
            B: When fetching only listed groups:
                1. Issue a FindCoordintorRequest for each group
                2. Attach a callback to each FindCoordinatorResponse that issues OffsetFetchRequests for that group
            Both:
                3. Attach a callback to each OffsetFetchRequest that parses the response
                   and saves the consumer group's offsets
        """
        # Store the list of futures on the object because some of the callbacks create/store additional futures and they
        # don't have access to variables scoped to this method, only to the object scope
        self._consumer_futures = []

        if self._monitor_unlisted_consumer_groups:
            for broker in self.kafka_client._client.cluster.brokers():
                list_groups_future = self.kafka_client._list_consumer_groups_send_request(broker.nodeId)
                list_groups_future.add_callback(self._list_groups_callback, broker.nodeId)
                self._consumer_futures.append(list_groups_future)
        elif self._consumer_groups:
            self.validate_consumer_groups()
            for consumer_group in self._consumer_groups:
                find_coordinator_future = self.kafka_client._find_coordinator_id_send_request(consumer_group)
                find_coordinator_future.add_callback(self._find_coordinator_callback, consumer_group)
                self._consumer_futures.append(find_coordinator_future)
        else:
            raise ConfigurationError(
                "Cannot fetch consumer offsets because no consumer_groups are specified and "
                "monitor_unlisted_consumer_groups is %s." % self._monitor_unlisted_consumer_groups
            )

        # Loop until all futures resolved.
        self.kafka_client._wait_for_futures(self._consumer_futures)
        del self._consumer_futures  # since it's reset on every check run, no sense holding the reference between runs

    def _list_groups_callback(self, broker_id, response):
        """Callback that takes a ListGroupsResponse and issues an OffsetFetchRequest for each group.

        broker_id must be manually passed in because it is not present in the response. Keeping track of the broker that
        gave us this response lets us skip issuing FindCoordinatorRequests because Kafka brokers only include
        consumer groups in their ListGroupsResponse when they are the coordinator for that group.
        """
        for consumer_group, group_type in self.kafka_client._list_consumer_groups_process_response(response):
            # consumer groups from Kafka < 0.9 that store their offset in Kafka don't use Kafka for group-coordination
            # so their group_type is empty
            if group_type in ('consumer', ''):
                single_group_offsets_future = self.kafka_client._list_consumer_group_offsets_send_request(
                    group_id=consumer_group, group_coordinator_id=broker_id
                )
                single_group_offsets_future.add_callback(self._single_group_offsets_callback, consumer_group)
                self._consumer_futures.append(single_group_offsets_future)

    def _find_coordinator_callback(self, consumer_group, response):
        """Callback that takes a FindCoordinatorResponse and issues an OffsetFetchRequest for the group.

        consumer_group must be manually passed in because it is not present in the response, but we need it in order to
        associate these offsets to the proper consumer group.

        The OffsetFetchRequest is scoped to the topics and partitions that are specified in the check config. If
        topics are unspecified, it will fetch all known offsets for that consumer group. Similarly, if the partitions
        are unspecified for a topic listed in the config, offsets are fetched for all the partitions within that topic.
        """
        coordinator_id = self.kafka_client._find_coordinator_id_process_response(response)
        topics = self._consumer_groups[consumer_group]
        if not topics:
            topic_partitions = None  # None signals to fetch all known offsets for the consumer group
        else:
            # transform [("t1", [1, 2])] into [TopicPartition("t1", 1), TopicPartition("t1", 2)]
            topic_partitions = []
            for topic, partitions in topics.items():
                if not partitions:  # If partitions aren't specified, fetch all partitions in the topic
                    partitions = self.kafka_client._client.cluster.partitions_for_topic(topic)
                topic_partitions.extend([TopicPartition(topic, p) for p in partitions])
        single_group_offsets_future = self.kafka_client._list_consumer_group_offsets_send_request(
            group_id=consumer_group, group_coordinator_id=coordinator_id, partitions=topic_partitions
        )
        single_group_offsets_future.add_callback(self._single_group_offsets_callback, consumer_group)
        self._consumer_futures.append(single_group_offsets_future)

    def _single_group_offsets_callback(self, consumer_group, response):
        """Callback that parses an OffsetFetchResponse and saves it to the consumer_offsets dict.

        consumer_group must be manually passed in because it is not present in the response, but we need it in order to
        associate these offsets to the proper consumer group.
        """
        single_group_offsets = self.kafka_client._list_consumer_group_offsets_process_response(response)
        for (topic, partition), (offset, _metadata) in single_group_offsets.items():
            # If the OffsetFetchRequest explicitly specified partitions, the offset could returned as -1, meaning there
            # is no recorded offset for that partition... for example, if the partition doesn't exist in the cluster.
            # So ignore it.
            if offset == -1:
                self.kafka_client._client.cluster.request_update()  # force metadata update on next poll()
                continue
            key = (consumer_group, topic, partition)
            self._consumer_offsets[key] = offset

    @AgentCheck.metadata_entrypoint
    def _collect_broker_metadata(self):
        version_data = [str(part) for part in self.kafka_client._client.check_version()]
        version_parts = {name: part for name, part in zip(('major', 'minor', 'patch'), version_data)}

        self.set_metadata(
            'version', '.'.join(version_data), scheme='parts', final_scheme='semver', part_map=version_parts
        )

    @staticmethod
    def batchify(iterable, batch_size):
        iterable = list(iterable)
        return (iterable[i : i + batch_size] for i in range(0, len(iterable), batch_size))
