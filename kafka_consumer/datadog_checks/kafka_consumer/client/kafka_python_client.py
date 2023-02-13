# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict
from time import time

from kafka import errors as kafka_errors
from kafka.protocol.admin import ListGroupsRequest
from kafka.protocol.commit import GroupCoordinatorRequest, OffsetFetchRequest
from kafka.protocol.offset import OffsetRequest, OffsetResetStrategy, OffsetResponse
from kafka.structs import TopicPartition
from six import iteritems, string_types

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS


class KafkaPythonClient:
    def __init__(self, check) -> None:
        self.check = check
        self.log = check.log
        self.kafka_client = check.kafka_client

    @AgentCheck.metadata_entrypoint
    def collect_broker_metadata(self):
        return self._collect_broker_metadata

    def _collect_broker_metadata(self):
        version_data = [str(part) for part in self.kafka_client._client.check_version()]
        version_parts = {name: part for name, part in zip(('major', 'minor', 'patch'), version_data)}

        self.set_metadata(
            'version', '.'.join(version_data), scheme='parts', final_scheme='semver', part_map=version_parts
        )

    def get_consumer_offsets(self):
        return self._get_consumer_offsets

    def get_broker_offset(self):
        return self._get_broker_offset

    def _get_broker_offset(self):
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
        if not self.check._monitor_all_broker_highwatermarks:
            tps_with_consumer_offset = {(topic, partition) for (_, topic, partition) in self.check._consumer_offsets}

        for batch in self.batchify(
            self.check.kafka_client._client.cluster.brokers(), self.check._broker_requests_batch_size
        ):
            for broker in batch:
                broker_led_partitions = self.check.kafka_client._client.cluster.partitions_for_broker(broker.nodeId)
                if broker_led_partitions is None:
                    continue

                # Take the partitions for which this broker is the leader and group them by topic in order to construct
                # the OffsetRequest while simultaneously filtering out partitions we want to exclude
                partitions_grouped_by_topic = defaultdict(list)
                for topic, partition in broker_led_partitions:
                    # No sense fetching highwater offsets for internal topics
                    if topic not in KAFKA_INTERNAL_TOPICS and (
                        self.check._monitor_all_broker_highwatermarks or (topic, partition) in tps_with_consumer_offset
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

                # We can disable wakeup here because it is the same thread doing both polling and sending. Also, it
                # is possible that the wakeup itself could block if a large number of sends were processed beforehand.
                highwater_future = self._send_request_to_node(node_id=broker.nodeId, request=request, wakeup=False)

                highwater_future.add_callback(self._highwater_offsets_callback)
                highwater_futures.append(highwater_future)

            # Loop until all futures resolved.
            self.check.kafka_client._wait_for_futures(highwater_futures)

    def _highwater_offsets_callback(self, response):
        """Callback that parses an OffsetFetchResponse and saves it to the highwater_offsets dict."""
        if type(response) not in OffsetResponse:
            raise RuntimeError("response type should be OffsetResponse, but instead was %s." % type(response))
        for topic, partitions_data in response.topics:
            for partition, error_code, offsets in partitions_data:
                error_type = kafka_errors.for_code(error_code)
                if error_type is kafka_errors.NoError:
                    self.check._highwater_offsets[(topic, partition)] = offsets[0]
                elif error_type is kafka_errors.NotLeaderForPartitionError:
                    self.check.log.warning(
                        "Kafka broker returned %s (error_code %s) for topic %s, partition: %s. This should only happen "
                        "if the broker that was the partition leader when kafka_admin_client last fetched metadata is "
                        "no longer the leader.",
                        error_type.message,
                        error_type.errno,
                        topic,
                        partition,
                    )
                    self.check.kafka_client._client.cluster.request_update()  # force metadata update on next poll()
                elif error_type is kafka_errors.UnknownTopicOrPartitionError:
                    self.check.log.warning(
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

    @staticmethod
    def batchify(iterable, batch_size):
        iterable = list(iterable)
        return (iterable[i : i + batch_size] for i in range(0, len(iterable), batch_size))

    # FIXME: This is using a workaround to skip socket wakeup, which causes blocking
    # (see https://github.com/dpkp/kafka-python/issues/2286).
    # Once https://github.com/dpkp/kafka-python/pull/2335 is merged in, we can use the official
    # implementation for this function instead.
    def _send_request_to_node(self, node_id, request, wakeup=True):
        while not self.check.kafka_client._client.ready(node_id):
            # poll until the connection to broker is ready, otherwise send()
            # will fail with NodeNotReadyError
            self.check.kafka_client._client.poll()
        return self.check.kafka_client._client.send(node_id, request, wakeup=wakeup)

    def report_consumer_offsets_and_lag(self):
        return self._report_consumer_offsets_and_lag

    def report_broker_offset(self, contexts_limit):
        return self._report_broker_offset

    def _report_broker_offset(self, contexts_limit):
        """Report the broker highwater offsets."""
        reported_contexts = 0
        self.log.debug("Reporting broker offset metric")
        for (topic, partition), highwater_offset in self._highwater_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            broker_tags.extend(self._custom_tags)
            self.gauge('broker_offset', highwater_offset, tags=broker_tags)
            reported_contexts += 1
            if reported_contexts == contexts_limit:
                return

    def _validate_consumer_groups(self):
        """Validate any explicitly specified consumer groups.

        consumer_groups = {'consumer_group': {'topic': [0, 1]}}
        """
        assert isinstance(self.check._consumer_groups, dict)
        for consumer_group, topics in self.check._consumer_groups.items():
            assert isinstance(consumer_group, string_types)
            assert isinstance(topics, dict) or topics is None  # topics are optional
            if topics is not None:
                for topic, partitions in topics.items():
                    assert isinstance(topic, string_types)
                    assert isinstance(partitions, (list, tuple)) or partitions is None  # partitions are optional
                    if partitions is not None:
                        for partition in partitions:
                            assert isinstance(partition, int)

    def _report_consumer_offsets_and_lag(self, contexts_limit):
        """Report the consumer offsets and consumer lag."""
        reported_contexts = 0
        self.log.debug("Reporting consumer offsets and lag metrics")
        for (consumer_group, topic, partition), consumer_offset in self.check._consumer_offsets.items():
            if reported_contexts >= contexts_limit:
                self.log.debug(
                    "Reported contexts number %s greater than or equal to contexts limit of %s, returning",
                    str(reported_contexts),
                    str(contexts_limit),
                )
                return
            consumer_group_tags = ['topic:%s' % topic, 'partition:%s' % partition, 'consumer_group:%s' % consumer_group]
            consumer_group_tags.extend(self.check._custom_tags)

            partitions = self.kafka_client._client.cluster.partitions_for_topic(topic)
            self.log.debug("Received partitions %s for topic %s", partitions, topic)
            if partitions is not None and partition in partitions:
                # report consumer offset if the partition is valid because even if leaderless the consumer offset will
                # be valid once the leader failover completes
                self.check.gauge('consumer_offset', consumer_offset, tags=consumer_group_tags)
                reported_contexts += 1

                if (topic, partition) not in self.check._highwater_offsets:
                    self.log.warning(
                        "Consumer group: %s has offsets for topic: %s partition: %s, but no stored highwater offset "
                        "(likely the partition is in the middle of leader failover) so cannot calculate consumer lag.",
                        consumer_group,
                        topic,
                        partition,
                    )
                    continue
                producer_offset = self.check._highwater_offsets[(topic, partition)]
                consumer_lag = producer_offset - consumer_offset
                if reported_contexts < contexts_limit:
                    self.check.gauge('consumer_lag', consumer_lag, tags=consumer_group_tags)
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
                    self._send_event(title, message, consumer_group_tags, 'consumer_lag', key, severity="error")
                    self.log.debug(message)
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

        if self.check._monitor_unlisted_consumer_groups:
            for broker in self.kafka_client._client.cluster.brokers():
                # FIXME: This is using a workaround to skip socket wakeup, which causes blocking
                # (see https://github.com/dpkp/kafka-python/issues/2286).
                # Once https://github.com/dpkp/kafka-python/pull/2335 is merged in, we can use the official
                # implementation for this function instead.
                list_groups_future = self._list_consumer_groups_send_request(broker.nodeId)
                list_groups_future.add_callback(self._list_groups_callback, broker.nodeId)
                self._consumer_futures.append(list_groups_future)
        elif self.check._consumer_groups:
            self._validate_consumer_groups()
            for consumer_group in self.check._consumer_groups:
                find_coordinator_future = self._find_coordinator_id_send_request(consumer_group)
                find_coordinator_future.add_callback(self._find_coordinator_callback, consumer_group)
                self._consumer_futures.append(find_coordinator_future)
        else:
            raise ConfigurationError(
                "Cannot fetch consumer offsets because no consumer_groups are specified and "
                "monitor_unlisted_consumer_groups is %s." % self.check._monitor_unlisted_consumer_groups
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
                single_group_offsets_future = self._list_consumer_group_offsets_send_request(
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
        topics = self.check._consumer_groups[consumer_group]
        if not topics:
            topic_partitions = None  # None signals to fetch all known offsets for the consumer group
        else:
            # transform [("t1", [1, 2])] into [TopicPartition("t1", 1), TopicPartition("t1", 2)]
            topic_partitions = []
            for topic, partitions in topics.items():
                if not partitions:  # If partitions aren't specified, fetch all partitions in the topic
                    partitions = self.kafka_client._client.cluster.partitions_for_topic(topic)
                topic_partitions.extend([TopicPartition(topic, p) for p in partitions])
        single_group_offsets_future = self._list_consumer_group_offsets_send_request(
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
        self.log.debug("Single group offsets: %s", single_group_offsets)
        for (topic, partition), (offset, _metadata) in single_group_offsets.items():
            # If the OffsetFetchRequest explicitly specified partitions, the offset could returned as -1, meaning there
            # is no recorded offset for that partition... for example, if the partition doesn't exist in the cluster.
            # So ignore it.
            if offset == -1:
                self.kafka_client._client.cluster.request_update()  # force metadata update on next poll()
                continue
            key = (consumer_group, topic, partition)
            self.check._consumer_offsets[key] = offset

    def _list_consumer_groups_send_request(self, broker_id):
        kafka_version = self.kafka_client._matching_api_version(ListGroupsRequest)
        if kafka_version <= 2:
            request = ListGroupsRequest[kafka_version]()
        else:
            raise NotImplementedError(
                "Support for ListGroupsRequest_v{} has not yet been added to KafkaAdminClient.".format(kafka_version)
            )
        # Disable wakeup when sending request to prevent blocking send requests
        return self.check._send_request_to_node(broker_id, request, wakeup=False)

    def _find_coordinator_id_send_request(self, group_id):
        """Send a FindCoordinatorRequest to a broker.
        :param group_id: The consumer group ID. This is typically the group
            name as a string.
        :return: A message future
        """
        version = 0
        request = GroupCoordinatorRequest[version](group_id)
        return self.check._send_request_to_node(self.kafka_client._client.least_loaded_node(), request, wakeup=False)

    def _list_consumer_group_offsets_send_request(self, group_id, group_coordinator_id, partitions=None):
        """Send an OffsetFetchRequest to a broker.
        :param group_id: The consumer group id name for which to fetch offsets.
        :param group_coordinator_id: The node_id of the group's coordinator
            broker.
        :return: A message future
        """
        version = self.kafka_client._matching_api_version(OffsetFetchRequest)
        if version <= 3:
            if partitions is None:
                if version <= 1:
                    raise ValueError(
                        """OffsetFetchRequest_v{} requires specifying the
                        partitions for which to fetch offsets. Omitting the
                        partitions is only supported on brokers >= 0.10.2.
                        For details, see KIP-88.""".format(
                            version
                        )
                    )
                topics_partitions = None
            else:
                # transform from [TopicPartition("t1", 1), TopicPartition("t1", 2)] to [("t1", [1, 2])]
                topics_partitions_dict = defaultdict(set)
                for topic, partition in partitions:
                    topics_partitions_dict[topic].add(partition)
                topics_partitions = list(iteritems(topics_partitions_dict))
            request = OffsetFetchRequest[version](group_id, topics_partitions)
        else:
            raise NotImplementedError(
                "Support for OffsetFetchRequest_v{} has not yet been added to KafkaAdminClient.".format(version)
            )
        return self.check._send_request_to_node(group_coordinator_id, request, wakeup=False)

    def _send_event(self, title, text, tags, event_type, aggregation_key, severity='info'):
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
        self.check.event(event_dict)
