# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict

from kafka import KafkaAdminClient
from kafka import errors as kafka_errors
from kafka.oauth.abstract import AbstractTokenProvider
from kafka.protocol.admin import ListGroupsRequest
from kafka.protocol.commit import GroupCoordinatorRequest, OffsetFetchRequest
from kafka.protocol.offset import OffsetRequest, OffsetResetStrategy, OffsetResponse
from kafka.structs import TopicPartition
from six import iteritems, string_types

from datadog_checks.base import ConfigurationError
from datadog_checks.base.utils.http import AuthTokenOAuthReader
from datadog_checks.kafka_consumer.client.kafka_client import KafkaClient
from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS


class OAuthTokenProvider(AbstractTokenProvider):
    def __init__(self, **config):
        self.reader = AuthTokenOAuthReader(config)

    def token(self):
        # Read only if necessary or use cached token
        return self.reader.read() or self.reader._token


class KafkaPythonClient(KafkaClient):
    def __init__(self, config, log, tls_context) -> None:
        self.config = config
        self.log = log
        self._kafka_client = None
        self._highwater_offsets = {}
        self._consumer_offsets = {}
        self.tls_context = tls_context

    def get_consumer_offsets(self):
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

        if self.config._monitor_unlisted_consumer_groups:
            for broker in self.kafka_client._client.cluster.brokers():
                # FIXME: This is using a workaround to skip socket wakeup, which causes blocking
                # (see https://github.com/dpkp/kafka-python/issues/2286).
                # Once https://github.com/dpkp/kafka-python/pull/2335 is merged in, we can use the official
                # implementation for this function instead.
                list_groups_future = self._list_consumer_groups_send_request(broker.nodeId)
                list_groups_future.add_callback(self._list_groups_callback, broker.nodeId)
                self._consumer_futures.append(list_groups_future)
        elif self.config._consumer_groups:
            self._validate_consumer_groups()
            for consumer_group in self.config._consumer_groups:
                find_coordinator_future = self._find_coordinator_id_send_request(consumer_group)
                find_coordinator_future.add_callback(self._find_coordinator_callback, consumer_group)
                self._consumer_futures.append(find_coordinator_future)
        else:
            raise ConfigurationError(
                "Cannot fetch consumer offsets because no consumer_groups are specified and "
                "monitor_unlisted_consumer_groups is %s." % self.config._monitor_unlisted_consumer_groups
            )

        # Loop until all futures resolved.
        self.kafka_client._wait_for_futures(self._consumer_futures)
        del self._consumer_futures  # since it's reset on every check run, no sense holding the reference between runs
        return self._consumer_offsets

    def get_highwater_offsets(self):
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
        if not self.config._monitor_all_broker_highwatermarks:
            tps_with_consumer_offset = {(topic, partition) for (_, topic, partition) in self._consumer_offsets}

        for batch in self.batchify(
            self.kafka_client._client.cluster.brokers(), self.config._broker_requests_batch_size
        ):
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
                        self.config._monitor_all_broker_highwatermarks or (topic, partition) in tps_with_consumer_offset
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
            self.kafka_client._wait_for_futures(highwater_futures)

            return self._highwater_offsets

    def create_kafka_admin_client(self):
        return self._create_kafka_client(clazz=KafkaAdminClient)

    def get_partitions_for_topic(self, topic):
        return self.kafka_client._client.cluster.partitions_for_topic(topic)

    def request_update(self):
        self.kafka_client._client.cluster.request_update()

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

    def _create_kafka_client(self, clazz):
        if not isinstance(self.config._kafka_connect_str, (string_types, list)):
            raise ConfigurationError('kafka_connect_str should be string or list of strings')

        return clazz(
            bootstrap_servers=self.config._kafka_connect_str,
            client_id='dd-agent',
            request_timeout_ms=self.config._request_timeout_ms,
            # if `kafka_client_api_version` is not set, then kafka-python automatically probes the cluster for
            # broker version during the bootstrapping process. Note that this returns the first version found, so in
            # a mixed-version cluster this will be a non-deterministic result.
            api_version=self.config._kafka_version,
            # While we check for SASL/SSL params, if not present they will default to the kafka-python values for
            # plaintext connections
            security_protocol=self.config._security_protocol,
            sasl_mechanism=self.config._sasl_mechanism,
            sasl_plain_username=self.config._sasl_plain_username,
            sasl_plain_password=self.config._sasl_plain_password,
            sasl_kerberos_service_name=self.config._sasl_kerberos_service_name,
            sasl_kerberos_domain_name=self.config._sasl_kerberos_domain_name,
            sasl_oauth_token_provider=(
                OAuthTokenProvider(**self.config._sasl_oauth_token_provider)
                if 'sasl_oauth_token_provider' in self.config.instance
                else None
            ),
            ssl_context=self.tls_context,
        )

    @property
    def kafka_client(self):
        if self._kafka_client is None:
            # if `kafka_client_api_version` is not set, then kafka-python automatically probes the cluster for
            # broker version during the bootstrapping process. Note that this returns the first version found, so in
            # a mixed-version cluster this will be a non-deterministic result.
            kafka_version = self.config._kafka_version

            self._kafka_client = self._create_kafka_admin_client(api_version=kafka_version)
        return self._kafka_client

    def get_version(self):
        return self.kafka_client._client.check_version()

    def _highwater_offsets_callback(self, response):
        """Callback that parses an OffsetFetchResponse and saves it to the highwater_offsets dict."""
        if type(response) not in OffsetResponse:
            raise RuntimeError("response type should be OffsetResponse, but instead was %s." % type(response))
        for topic, partitions_data in response.topics:
            for partition, error_code, offsets in partitions_data:
                error_type = kafka_errors.for_code(error_code)
                if error_type is kafka_errors.NoError:
                    self._highwater_offsets[(topic, partition)] = offsets[0]
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

    @staticmethod
    def batchify(iterable, batch_size):
        iterable = list(iterable)
        return (iterable[i : i + batch_size] for i in range(0, len(iterable), batch_size))

    # FIXME: This is using a workaround to skip socket wakeup, which causes blocking
    # (see https://github.com/dpkp/kafka-python/issues/2286).
    # Once https://github.com/dpkp/kafka-python/pull/2335 is merged in, we can use the official
    # implementation for this function instead.
    def _send_request_to_node(self, node_id, request, wakeup=True):
        while not self.kafka_client._client.ready(node_id):
            # poll until the connection to broker is ready, otherwise send()
            # will fail with NodeNotReadyError
            self.kafka_client._client.poll()
        return self.kafka_client._client.send(node_id, request, wakeup=wakeup)

    def _validate_consumer_groups(self):
        """Validate any explicitly specified consumer groups.

        consumer_groups = {'consumer_group': {'topic': [0, 1]}}
        """
        assert isinstance(self.config._consumer_groups, dict)
        for consumer_group, topics in self.config._consumer_groups.items():
            assert isinstance(consumer_group, string_types)
            assert isinstance(topics, dict) or topics is None  # topics are optional
            if topics is not None:
                for topic, partitions in topics.items():
                    assert isinstance(topic, string_types)
                    assert isinstance(partitions, (list, tuple)) or partitions is None  # partitions are optional
                    if partitions is not None:
                        for partition in partitions:
                            assert isinstance(partition, int)

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
        topics = self.config._consumer_groups[consumer_group]
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
            self._consumer_offsets[key] = offset

    def _list_consumer_groups_send_request(self, broker_id):
        kafka_version = self.kafka_client._matching_api_version(ListGroupsRequest)
        if kafka_version <= 2:
            request = ListGroupsRequest[kafka_version]()
        else:
            raise NotImplementedError(
                "Support for ListGroupsRequest_v{} has not yet been added to KafkaAdminClient.".format(kafka_version)
            )
        # Disable wakeup when sending request to prevent blocking send requests
        return self._send_request_to_node(broker_id, request, wakeup=False)

    def _find_coordinator_id_send_request(self, group_id):
        """Send a FindCoordinatorRequest to a broker.
        :param group_id: The consumer group ID. This is typically the group
            name as a string.
        :return: A message future
        """
        version = 0
        request = GroupCoordinatorRequest[version](group_id)
        return self._send_request_to_node(self.kafka_client._client.least_loaded_node(), request, wakeup=False)

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
        return self._send_request_to_node(group_coordinator_id, request, wakeup=False)
