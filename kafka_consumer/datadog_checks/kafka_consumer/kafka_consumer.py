# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
from time import time

# 3p
from kafka import KafkaAdminClient, errors as kafka_errors
from kafka.protocol.offset import OffsetRequest, OffsetResponse, OffsetResetStrategy
from kafka.structs import TopicPartition
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError
from six import iteritems, string_types

# project
from datadog_checks.base import AgentCheck

DEFAULT_KAFKA_TIMEOUT = 5
DEFAULT_ZK_TIMEOUT = 5

CONTEXT_UPPER_BOUND = 200

WARNING_BROKER_LESS_THAN_0_10_2 = ("Broker versions < 0.10.2.0 do not support "
    "OffsetFetchRequest_v2, so the consumer groups and topics must be "
    "specified. The partitions are optional. For details, see KIP-88.")


class BadKafkaConsumerConfiguration(Exception):
    pass


class KafkaCheck(AgentCheck):
    """
    Check the offsets and lag of Kafka consumers.

    For details about the supported options, see the associated
    `conf.yaml.example`.

    This check also returns broker highwater offsets.
    """

    SOURCE_TYPE_NAME = 'kafka'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        # Cache for long-lived KafkaAdminClients
        self.kafka_clients = {}

    def check(self, instance):
        """The main entrypoint of the check."""
        custom_tags = instance.get('tags', [])
        kafka_admin_client = self._get_kafka_admin_client(instance)

        # For calculating consumer lag, we have to fetch both the consumer
        # offset and the broker highwater offset. There's a potential race
        # condition because whichever one we check first may be outdated by the
        # time we check the other. Better to check consumer offsets before
        # checking broker offsets because worst case is that overstates
        # consumer lag a little. Doing it the other way can understate consumer
        # lag to the point of having negative consumer lag, which just creates
        # confusion because it's theoretically impossible.

        consumer_offset_sources = self._determine_where_to_fetch_consumer_offsets(instance)

        # Fetch Zookeeper consumer offsets
        zk_consumer_offsets = None
        if 'zookeeper' in consumer_offset_sources:
            try:
                zk_consumer_offsets = self._get_zk_consumer_offsets(
                    zk_connect_str=instance.get('zk_connect_str'),
                    consumer_groups=self._determine_which_consumer_groups_to_fetch(instance, source='zookeeper'),
                    zk_prefix=instance.get('zk_prefix', ''),
                )
            except Exception:
                # don't raise because we might get valid Kafka consumer / broker offsets
                self.log.exception("There was a problem collecting consumer offsets from Zookeeper.")
                pass

        # Fetch Kafka consumer offsets
        kafka_consumer_offsets = None
        if 'kafka' in consumer_offset_sources:
            try:
                kafka_consumer_offsets = self._get_kafka_consumer_offsets(
                    kafka_admin_client=kafka_admin_client,
                    consumer_groups=self._determine_which_consumer_groups_to_fetch(instance, source='kafka'),
                )
            except Exception:
                # don't raise because we might get valid Zookeeper / broker offsets
                self.log.exception("There was a problem collecting consumer offsets from Kafka.")
                pass

        context_limit = self.init_config.get('max_partition_contexts', CONTEXT_UPPER_BOUND)
        warn_msg = """ Discovered %s partition contexts - this exceeds the
                       maximum number of %s contexts permitted by the check.
                       Please narrow your target by specifying in your
                       kafka_consumer.yaml the consumer groups, topics and
                       partitions you wish to monitor."""
        if zk_consumer_offsets is not None and len(zk_consumer_offsets) > context_limit:
            self.warning(warn_msg % (len(zk_consumer_offsets), context_limit))
            return
        if kafka_consumer_offsets is not None and len(kafka_consumer_offsets) > context_limit:
            self.warning(warn_msg % (len(kafka_consumer_offsets), context_limit))
            return

        # Fetch the broker highwater offsets
        try:
            highwater_offsets, topic_partitions_without_a_leader = self._get_broker_offsets(kafka_admin_client)
        except Exception:
            self.log.exception("There was a problem collecting the highwater mark offsets.")
            # Unlike consumer offsets, fail immediately because we can't
            # calculate consumer lag w/o highwater_offsets
            raise

        # Report the broker highwater offset
        for (topic, partition), highwater_offset in iteritems(highwater_offsets):
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition] + custom_tags
            self.gauge('kafka.broker_offset', highwater_offset, tags=broker_tags)

        # Report the consumer group offsets and consumer lag
        if zk_consumer_offsets is not None:
            self._report_consumer_metrics(highwater_offsets, zk_consumer_offsets,
                                          topic_partitions_without_a_leader, tags=custom_tags + ['source:zk'])
        if kafka_consumer_offsets is not None:
            self._report_consumer_metrics(highwater_offsets, kafka_consumer_offsets,
                                          topic_partitions_without_a_leader, tags=custom_tags + ['source:kafka'])

    def _get_kafka_admin_client(self, instance):
        """Given an instance of the check, cache and return a KafkaAdminClient.

        Note: Ideally we could store the generated client object on the
            instance, but in agent v5, self is the agent object, and when I
            tried to store it on the instance, the bowels of the datadog agent
            code started throwing weird exceptions. So for now the clients
            are cached on the agent object. However, I _think_ in agent v6
            `self` switches to the check instance object. If so, update this
            method to directly store the client on `self` and access as needed.
        """
        kafka_connect_str = instance.get('kafka_connect_str')
        if not isinstance(kafka_connect_str, (string_types, list)):
            raise BadKafkaConsumerConfiguration(
                    "kafka_connect_str should be a string or list of strings")

        instance_key = tuple(kafka_connect_str)  # cast to tuple in case it's a list
        if instance_key not in self.kafka_clients:
            self.kafka_clients[instance_key] = KafkaAdminClient(
                bootstrap_servers=kafka_connect_str,
                client_id='dd-agent',
                request_timeout_ms=self.init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT)*1000,
                api_version=instance.get('kafka_client_api_version'),
                # While we check for SSL params, if not present they will default
                # to the kafka-python values for plaintext connections
                security_protocol=instance.get('security_protocol', 'PLAINTEXT'),
                ssl_cafile=instance.get('ssl_cafile'),
                ssl_check_hostname=instance.get('ssl_check_hostname', True),
                ssl_certfile=instance.get('ssl_certfile'),
                ssl_keyfile=instance.get('ssl_keyfile'),
                ssl_password=instance.get('ssl_password'),
            )
        return self.kafka_clients[instance_key]

    def _determine_where_to_fetch_consumer_offsets(self, instance):
        """Determine whether to fetch consumer offsets from Kafka, Zookeeper,
        both, or neither.

        Returns:
            consumer_offset_sources (set): The set of sources from which to
                fetch offsets. Valid values are the strings 'kafka' and
                'zookeeper'. The set may contain one, both, or neither.
        """
        consumer_offset_sources = set()
        zk_specified = bool(instance.get('zk_connect_str'))
        if zk_specified:
            consumer_offset_sources.add('zookeeper')
        # Brokers < 0.8.2 can't store consumer offsets.
        broker_supports_storing_consumer_offsets = self._get_kafka_admin_client(instance).config['api_version'] >= (0, 8, 2)
        if broker_supports_storing_consumer_offsets \
                and (not zk_specified or instance.get('kafka_consumer_offsets') is True):
            consumer_offset_sources.add('kafka')
        return consumer_offset_sources

    def _determine_which_consumer_groups_to_fetch(self, instance, source):
        """Determine which consumer groups to fetch offsets for.

        This is based on the source of the offsets, the instance configuration,
        and the kafka cluster version. In particular, this handles the edge
        case where the source is 'kafka' but if the broker < 0.10.2 then the
        value of `monitor_unlisted_consumer_groups` must be ignored.

        NOTE: The check configuration does not provide a way to specify whether
            a consumer group stores its offsets in Kafka or Zookeeper. It's
            also technically valid for the group to double-commit its offsets.
            So rather than trying to be smart about this, we check for offsets
            in both places and report whatever we found.

        Arguments:
            source (string): Either 'kafka' or 'zookeeper'

        Returns:
            consumer_groups (dict): The consumer groups, topics, and partitions
                for which you want to fetch offsets. Can also return None,
                which typically will be used as a signal to discover/fetch all
                known offsets. For examples of what this dict can look like,
                see _validate_explicit_consumer_groups().
        """
        # brokers < 0.10.2 require specifying consumer_groups with topics

        old_broker = self._get_kafka_admin_client(instance).config['api_version'] < (0, 10, 2)
        if instance.get('monitor_unlisted_consumer_groups') and \
                (not source == 'kafka' or (source == 'kafka' and not old_broker)):
            return
        listed_consumer_groups = instance.get('consumer_groups')
        if listed_consumer_groups is not None:
            self._validate_listed_consumer_groups(listed_consumer_groups)
            return listed_consumer_groups
        else:
            error_msg = ("Cannot fetch consumer offsets because no "
                "consumer_groups are specified and monitor_unlisted_consumer_groups "
                "is %s." % instance.get('monitor_unlisted_consumer_groups'))
            if source == 'kafka' and old_broker:
                error_msg += (" " + WARNING_BROKER_LESS_THAN_0_10_2)
            raise BadKafkaConsumerConfiguration(error_msg)

    def _get_kafka_consumer_offsets(self, kafka_admin_client, consumer_groups=None):
        """Fetch Consumer Group offsets from Kafka.

        Also fetch consumer_groups, topics, and partitions if not
        already specified in consumer_groups.

        Arguments:
            consumer_groups (dict): The consumer groups, topics, and partitions
                for which you want to fetch offsets. If consumer_groups is
                None, will fetch offsets for all consumer_groups. For examples
                of what this dict can look like, see
                _validate_explicit_consumer_groups().

        Returns:
            dict: {(consumer_group, topic, partition): consumer_offset} where
                consumer_offset is an integer.
        """
        consumer_offsets = {}
        old_broker = kafka_admin_client.config['api_version'] < (0, 10, 2)
        if consumer_groups is None:  # None signals to fetch all from Kafka
            if old_broker:
                raise BadKafkaConsumerConfiguration(WARNING_BROKER_LESS_THAN_0_10_2)
            for broker in kafka_admin_client._client.cluster.brokers():
                for consumer_group, group_type in kafka_admin_client.list_consumer_groups(broker_ids=[broker.nodeId]):
                    # consumer groups from Kafka < 0.9 that store their offset
                    # in Kafka don't use Kafka for group-coordination so
                    # group_type is empty
                    if group_type in ('consumer', ''):
                        # Typically the consumer group offset fetch sequence is:
                        # 1. For each broker in the cluster, send a ListGroupsRequest
                        # 2. For each consumer group, send a FindGroupCoordinatorRequest
                        # 3. Query the group coordinator for the consumer's offsets.
                        # However, since Kafka brokers only include consumer
                        # groups in their ListGroupsResponse when they are the
                        # coordinator for that group, we can skip the
                        # FindGroupCoordinatorRequest.
                        this_group_offsets = kafka_admin_client.list_consumer_group_offsets(
                            group_id=consumer_group, group_coordinator_id=broker.nodeId)
                        for (topic, partition), (offset, metadata) in iteritems(this_group_offsets):
                            key = (consumer_group, topic, partition)
                            consumer_offsets[key] = offset
        else:
            for consumer_group, topics in iteritems(consumer_groups):
                if topics is None:
                    if old_broker:
                        raise BadKafkaConsumerConfiguration(WARNING_BROKER_LESS_THAN_0_10_2)
                    topic_partitions = None
                else:
                    topic_partitions = []
                    # transform from [("t1", [1, 2])] to [TopicPartition("t1", 1), TopicPartition("t1", 2)]
                    for topic, partitions in iteritems(topics):
                        if partitions is None:
                            # If partitions aren't specified, fetch all
                            # partitions in the topic from Kafka
                            partitions = kafka_admin_client._client.cluster.partitions_for_topic(topic)
                        topic_partitions.extend([TopicPartition(topic, p) for p in partitions])
                this_group_offsets = kafka_admin_client.list_consumer_group_offsets(consumer_group, partitions=topic_partitions)
                for (topic, partition), (offset, metadata) in iteritems(this_group_offsets):
                    # when we are explicitly specifying partitions, the offset
                    # could returned as -1, meaning there is no recorded offset
                    # for that partition... for example, if the partition
                    # doesn't exist in the cluster. So ignore it.
                    if offset != -1:
                        key = (consumer_group, topic, partition)
                        consumer_offsets[key] = offset

        return consumer_offsets

    def _get_zk_path_children(self, zk_conn, zk_path, name_for_error):
        """Fetch child nodes for a given Zookeeper path."""
        children = []
        try:
            children = zk_conn.get_children(zk_path)
        except NoNodeError:
            self.log.info('No zookeeper node at %s', zk_path)
        except Exception:
            self.log.exception('Could not read %s from %s', name_for_error, zk_path)
        return children

    def _get_zk_consumer_offsets(self, zk_connect_str, consumer_groups=None, zk_prefix=''):
        """
        Fetch Consumer Group offsets from Zookeeper.

        Also fetch consumer_groups, topics, and partitions if not
        already specified in consumer_groups.

        Arguments:
            consumer_groups (dict): The consumer groups, topics, and partitions
                that you want to fetch offsets for. If consumer_groups is None,
                will fetch offsets for all consumer_groups. For examples of
                what this dict can look like, see
                _validate_explicit_consumer_groups().

        Returns:
            dict: {(consumer_group, topic, partition): consumer_offset} where
                consumer_offset is an integer.
        """
        consumer_offsets = {}

        # Construct the Zookeeper path pattern
        # /consumers/[groupId]/offsets/[topic]/[partitionId]
        zk_path_consumer = zk_prefix + '/consumers/'
        zk_path_topic_tmpl = zk_path_consumer + '{group}/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '{topic}/'

        if not isinstance(zk_connect_str, (string_types, list)):
            raise BadKafkaConsumerConfiguration(
                    "zk_connect_str should be a string or list of strings")
        zk_conn = KazooClient(
            hosts=zk_connect_str,
            timeout=self.init_config.get('zk_timeout', DEFAULT_ZK_TIMEOUT)
        )
        zk_conn.start()
        try:
            if consumer_groups is None:
                # If consumer groups aren't specified, fetch them from ZK
                consumer_groups = {consumer_group: None for consumer_group in
                                   self._get_zk_path_children(zk_conn, zk_path_consumer, 'consumer groups')}

            for consumer_group, topics in iteritems(consumer_groups):
                if topics is None:
                    # If topics are't specified, fetch them from ZK
                    zk_path_topics = zk_path_topic_tmpl.format(group=consumer_group)
                    topics = {topic: None for topic in
                              self._get_zk_path_children(zk_conn, zk_path_topics, 'topics')}
                    consumer_groups[consumer_group] = topics

                for topic, partitions in iteritems(topics):
                    if partitions is None:
                        # If partitions aren't specified, fetch them from ZK
                        zk_path_partitions = zk_path_partition_tmpl.format(group=consumer_group, topic=topic)
                        # Zookeeper returns the partition IDs as strings because
                        # they are extracted from the node path
                        partitions = [int(x) for x in self._get_zk_path_children(
                            zk_conn, zk_path_partitions, 'partitions')]
                        consumer_groups[consumer_group][topic] = partitions

                    # Fetch consumer offsets for each partition from ZK
                    for partition in partitions:
                        zk_path = (zk_path_partition_tmpl + '{partition}/').format(
                            group=consumer_group, topic=topic, partition=partition)
                        try:
                            consumer_offset = int(zk_conn.get(zk_path)[0])
                            key = (consumer_group, topic, partition)
                            consumer_offsets[key] = consumer_offset
                        except NoNodeError:
                            self.log.info('No zookeeper node at %s', zk_path)
                        except Exception:
                            self.log.exception('Could not read consumer offset from %s', zk_path)
        finally:
            try:
                zk_conn.stop()
                zk_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Zookeeper connection')
        return consumer_offsets

    def _get_broker_offsets(self, kafka_admin_client, topics=None):
        """Fetch highwater offsets for topic_partitions in the Kafka cluster.

        Do this for all partitions in the cluster because even if it has no
        consumers, we may want to measure whether producers are successfully
        producing. No need to limit this for performance because fetching
        broker offsets from Kafka is a relatively inexpensive operation.

        Internal Kafka topics like __consumer_offsets are excluded.

        Sends one OffsetRequest per broker to get offsets for all partitions
        where that broker is the leader:
        https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetAPI(AKAListOffset)

        Arguments:
            topics (set): The set of topics (as strings) for which to fetch
                highwater offsets. If set to None, will fetch highwater offsets
                for all topics in the cluster.
        """
        highwater_offsets = {}
        topic_partitions_without_a_leader = set()

        # No sense fetching highwatever offsets for internal topics
        internal_topics = {
            '__consumer_offsets',
            '__transaction_state',
            '_schema',  # Confluent registry topic
        }

        for broker in kafka_admin_client._client.cluster.brokers():
            broker_led_partitions = kafka_admin_client._client.cluster.partitions_for_broker(broker.nodeId)
            # Take the partitions for which this broker is the leader and group
            # them by topic in order to construct the OffsetRequest.
            # Any partitions that don't currently have a leader will be skipped.
            partitions_grouped_by_topic = defaultdict(list)
            if broker_led_partitions is None:
                continue
            for topic, partition in broker_led_partitions:
                if topic in internal_topics or (topics is not None and topic not in topics):
                    continue
                partitions_grouped_by_topic[topic].append(partition)

            # Construct the OffsetRequest
            max_offsets = 1
            request = OffsetRequest[0](
                replica_id=-1,
                topics=[
                    (topic, [(partition, OffsetResetStrategy.LATEST, max_offsets) for partition in partitions])
                    for topic, partitions in iteritems(partitions_grouped_by_topic)])
            response = kafka_admin_client._send_request_to_node(node_id=broker.nodeId, request=request)
            offsets, unled = self._process_highwater_offsets(response)
            highwater_offsets.update(offsets)
            topic_partitions_without_a_leader.update(unled)

        return highwater_offsets, topic_partitions_without_a_leader

    def _process_highwater_offsets(self, response):
        """Convert OffsetFetchResponse to a dictionary of offsets.

        Returns: A dictionary with TopicPartition keys and integer offsets:
            {TopicPartition: offset}. Also returns a set of TopicPartitions
            without a leader.
        """
        highwater_offsets = {}
        topic_partitions_without_a_leader = set()
        assert isinstance(response, OffsetResponse[0])
        for topic, partitions_data in response.topics:
            for partition, error_code, offsets in partitions_data:
                topic_partition = TopicPartition(topic, partition)
                error_type = kafka_errors.for_code(error_code)
                if error_type is kafka_errors.NoError:
                    highwater_offsets[topic_partition] = offsets[0]
                # Valid error codes:
                # https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-PossibleErrorCodes.2
                elif error_type is kafka_errors.NotLeaderForPartitionError:
                    self.log.warn("Kafka broker returned %s (error_code %s) "
                        "for topic: %s, partition: %s. This should only happen "
                        "if the broker that was the partition leader when "
                        "kafka_admin_client last fetched metadata is no "
                        "longer the leader.", error_type.message,
                        error_type.errno, topic, partition)
                    topic_partitions_without_a_leader.add(topic_partition)
                elif error_type is kafka_errors.UnknownTopicOrPartitionError:
                    self.log.warn("Kafka broker returned %s (error_code %s) "
                        "for topic: %s, partition: %s. This should only happen "
                        "if the topic is currently being deleted or the check "
                        "configuration lists non-existent partitions.",
                        error_type.message, error_type.errno, topic, partition)
                else:
                    raise error_type("Unexpected error encountered while "
                        "attempting to fetch the highwater offsets for topic: "
                        "%s, partition: %s." % (topic, partition))
        assert topic_partitions_without_a_leader.isdisjoint(highwater_offsets)
        return highwater_offsets, topic_partitions_without_a_leader

    def _report_consumer_metrics(self, highwater_offsets, consumer_offsets,
            topic_partitions_without_a_leader=None, tags=None):
        """Report the consumer offsets and consumer lag."""
        if topic_partitions_without_a_leader is None:
            topic_partitions_without_a_leader = []
        if tags is None:
            tags = []
        for (consumer_group, topic, partition), consumer_offset in iteritems(consumer_offsets):
            consumer_group_tags = ['topic:%s' % topic, 'partition:%s' % partition,
                                   'consumer_group:%s' % consumer_group] + tags
            if (topic, partition) in highwater_offsets or (topic, partition) in topic_partitions_without_a_leader:
                # report consumer offset even if the partition leader is unknown
                # because the offset will be valid once the leader failover completes
                self.gauge('kafka.consumer_offset', consumer_offset, tags=consumer_group_tags)

                if (topic, partition) in topic_partitions_without_a_leader:
                    self.log.warn("Consumer group: %s has offsets for topic: %s"
                        "partition: %s, but no broker is currently the leader "
                        "of that partition so cannot calculate consumer lag.",
                        consumer_group, topic, partition)
                    continue

                consumer_lag = highwater_offsets[(topic, partition)] - consumer_offset
                if consumer_lag < 0:
                    # this will effectively result in data loss, so emit an
                    # event for max visibility
                    title = "Negative consumer lag for group: {}.".format(consumer_group)
                    message = ("Consumer group: {}, topic: {}, partition: {} "
                        "has negative consumer lag. This should never happen "
                        "and will result in the consumer skipping new messages."
                        .format(consumer_group, topic, partition))
                    key = "{}:{}:{}".format(consumer_group, topic, partition)
                    self._send_event(title, message, consumer_group_tags, 'consumer_lag',
                                    key, severity="error")
                    self.log.debug(message)
                self.gauge('kafka.consumer_lag', consumer_lag, tags=consumer_group_tags)

            else:
                self.log.warn("Consumer group: %s has offsets for topic: %s, "
                    "partition: %s, but that topic partition doesn't actually "
                    "exist in the cluster so skipping reporting these offsets.",
                    consumer_group, topic, partition)

    @classmethod
    def _validate_listed_consumer_groups(cls, val):
        """Validate any listed consumer groups.

        While the check does not require listing consumer groups,
        if they are specified this method should be used to validate them.

        val = {'consumer_group': {'topic': [0, 1]}}
        """
        # TODO can I allow consumer_groups to be a list rather than requiring a dict?
        assert isinstance(val, dict)
        for consumer_group, topics in iteritems(val):
            assert isinstance(consumer_group, string_types)
            # topics are optional
            assert isinstance(topics, dict) or topics is None
            if topics is not None:
                for topic, partitions in iteritems(topics):
                    assert isinstance(topic, string_types)
                    # partitions are optional
                    assert isinstance(partitions, (list, tuple)) or partitions is None
                    if partitions is not None:
                        for partition in partitions:
                            assert isinstance(partition, int)

    def _send_event(self, title, text, tags, event_type, aggregation_key, severity='info'):
        """Emit an event to the Datadog Event Stream."""
        event_dict = {
            'timestamp': int(time()),
            'source_type_name': self.SOURCE_TYPE_NAME,
            'msg_title': title,
            'event_type': event_type,
            'alert_type': severity,
            'msg_text': text,
            'tags': tags,
            'aggregation_key': aggregation_key,
        }
        self.event(event_dict)
