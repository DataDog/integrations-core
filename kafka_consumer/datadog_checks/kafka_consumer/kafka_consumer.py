# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from collections import defaultdict
import random
from time import time, sleep

# 3p
from kafka.client import KafkaClient
import kafka.errors as KafkaErrors
from kafka.protocol.commit import GroupCoordinatorRequest, OffsetFetchRequest
from kafka.protocol.offset import OffsetRequest, OffsetResetStrategy
from kafka.structs import TopicPartition
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError

# project
from datadog_checks.checks import AgentCheck
from datadog_checks.config import _is_affirmative

# Kafka Errors
KAFKA_NO_ERROR = KafkaErrors.NoError.errno
KAFKA_UNKNOWN_ERROR = KafkaErrors.UnknownError.errno
KAFKA_UNKNOWN_TOPIC_OR_PARTITION = KafkaErrors.UnknownTopicOrPartitionError.errno
KAFKA_NOT_LEADER_FOR_PARTITION = KafkaErrors.NotLeaderForPartitionError.errno

DEFAULT_KAFKA_TIMEOUT = 5
DEFAULT_ZK_TIMEOUT = 5
DEFAULT_KAFKA_RETRIES = 3

CONTEXT_UPPER_BOUND = 200


class BadKafkaConsumerConfiguration(Exception):
    pass


class KafkaCheck(AgentCheck):
    """
    Check the offsets and lag of Kafka consumers.

    This check also returns broker highwater offsets.
    """

    SOURCE_TYPE_NAME = 'kafka'

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances=instances)
        self._zk_timeout = int(
            init_config.get('zk_timeout', DEFAULT_ZK_TIMEOUT))
        self._kafka_timeout = int(
            init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT))
        self.context_limit = int(
            init_config.get('max_partition_contexts', CONTEXT_UPPER_BOUND))
        self._broker_retries = int(
            init_config.get('kafka_retries', DEFAULT_KAFKA_RETRIES))
        self._zk_last_ts = {}

        self.kafka_clients = {}

    def check(self, instance):
        # For calculating lag, we have to fetch offsets from both kafka and
        # zookeeper. There's a potential race condition because whichever one we
        # check first may be outdated by the time we check the other. Better to
        # check consumer offset before checking broker offset because worst case
        # is that overstates consumer lag a little. Doing it the other way can
        # understate consumer lag to the point of having negative consumer lag,
        # which just creates confusion because it's theoretically impossible.

        # Fetch consumer group offsets from Zookeeper
        zk_hosts_ports = instance.get('zk_connect_str')
        zk_prefix = instance.get('zk_prefix', '')
        zk_interval = int(instance.get('zk_iteration_ival', 0))
        get_kafka_consumer_offsets = _is_affirmative(
            instance.get('kafka_consumer_offsets', zk_hosts_ports is None))

        custom_tags = instance.get('tags', [])

        # If monitor_unlisted_consumer_groups is True, fetch all groups stored in ZK
        consumer_groups = None
        if instance.get('monitor_unlisted_consumer_groups', False):
            consumer_groups = None
        elif 'consumer_groups' in instance:
            consumer_groups = instance.get('consumer_groups')
            self._validate_explicit_consumer_groups(consumer_groups)

        zk_consumer_offsets = None
        if zk_hosts_ports and \
                self._should_zk(zk_hosts_ports, zk_interval, get_kafka_consumer_offsets):
            zk_consumer_offsets, consumer_groups = self._get_zk_consumer_offsets(
                zk_hosts_ports, consumer_groups, zk_prefix)

        topics = defaultdict(set)
        kafka_consumer_offsets = None

        cli = self._get_kafka_client(instance)
        cli._maybe_refresh_metadata()

        if get_kafka_consumer_offsets:
            # For now, consumer groups are mandatory if not using ZK
            if not zk_hosts_ports and not consumer_groups:
                raise BadKafkaConsumerConfiguration('Invalid configuration - if you\'re not collecting '
                                                    'offsets from ZK you _must_ specify consumer groups')
            # kafka-python automatically probes the cluster for broker version
            # and then stores it. Note that this returns the first version
            # found, so in a mixed-version cluster this will be a
            # non-deterministic result.
            #
            # Kafka 0.8.2 added support for storing consumer offsets in Kafka.
            if cli.config.get('api_version') >= (0, 8, 2):
                kafka_consumer_offsets, topics = self._get_kafka_consumer_offsets(instance, consumer_groups)

        if not topics:
            # val = {'consumer_group': {'topic': [0, 1]}}
            for _, tps in consumer_groups.iteritems():
                for topic, partitions in tps.iteritems():
                    topics[topic].update(partitions)

        warn_msg = """ Discovered %s partition contexts - this exceeds the maximum
                       number of contexts permitted by the check. Please narrow your
                       target by specifying in your YAML what consumer groups, topics
                       and partitions you wish to monitor."""
        if zk_consumer_offsets and len(zk_consumer_offsets) > self.context_limit:
            self.warning(warn_msg % len(zk_consumer_offsets))
            return
        if kafka_consumer_offsets and len(kafka_consumer_offsets) > self.context_limit:
            self.warning(warn_msg % len(kafka_consumer_offsets))
            return

        # Fetch the broker highwater offsets
        try:
            highwater_offsets, topic_partitions_without_a_leader = self._get_broker_offsets(instance, topics)
        except Exception:
            self.log.exception('There was a problem collecting the high watermark offsets')
            return

        # Report the broker highwater offset
        for (topic, partition), highwater_offset in highwater_offsets.iteritems():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition] + custom_tags
            self.gauge('kafka.broker_offset', highwater_offset, tags=broker_tags)

        # Report the consumer group offsets and consumer lag
        if zk_consumer_offsets:
            self._report_consumer_metrics(highwater_offsets, zk_consumer_offsets,
                                          topic_partitions_without_a_leader, tags=custom_tags + ['source:zk'])
        if kafka_consumer_offsets:
            self._report_consumer_metrics(highwater_offsets, kafka_consumer_offsets,
                                          topic_partitions_without_a_leader, tags=custom_tags + ['source:kafka'])

    def stop(self):
        """
        cleanup kafka connections (to all brokers) to avoid leaving
        stale connections in older kafkas.
        """
        for cli in self.kafka_clients.itervalues():
            cli.close()

    def _get_kafka_client(self, instance):
        kafka_conn_str = instance.get('kafka_connect_str')
        if not isinstance(kafka_conn_str, (basestring, list)):
            raise BadKafkaConsumerConfiguration(
                    'kafka_connect_str should be string or list of strings')

        instance_key = tuple(kafka_conn_str)  # cast to tuple in case it's a list
        if instance_key not in self.kafka_clients:
            # While we check for SSL params, if not present they will default
            # to the kafka-python values for plaintext connections
            cli = KafkaClient(bootstrap_servers=kafka_conn_str,
                              client_id='dd-agent',
                              security_protocol=instance.get('security_protocol', 'PLAINTEXT'),
                              ssl_cafile=instance.get('ssl_cafile'),
                              ssl_check_hostname=instance.get('ssl_check_hostname', True),
                              ssl_certfile=instance.get('ssl_certfile'),
                              ssl_keyfile=instance.get('ssl_keyfile'),
                              ssl_password=instance.get('ssl_password'))
            self.kafka_clients[instance_key] = cli

        return self.kafka_clients[instance_key]

    def _ensure_ready_node(self, client, node_id):
        if node_id is None:
            raise Exception("node_id is None")

        attempts = 0
        while not client.ready(node_id):
            if attempts > DEFAULT_KAFKA_RETRIES:
                self.log.error("unable to connect to broker id: %i after %i attempts",
                               node_id, DEFAULT_KAFKA_RETRIES)
                break
            attempts = attempts + 1
            delay = (2 ** attempts) + (random.randint(0, 1000) / 1000) * 0.01  # starting at 20 ms

            future = client.cluster.request_update()
            client.poll(future=future)
            if future.failed():
                if future.retriable():
                    if isinstance(future.exception, KafkaErrors.NodeNotReadyError):
                        self.log.debug("broker id: %s is not ready yet, sleeping for %f ms", node_id, delay * 10)
                        sleep(delay)
                        continue

                raise future.exception

    def _make_blocking_req(self, client, request, node_id=None):
        if node_id is None:
            node_id = client.least_loaded_node()

        self._ensure_ready_node(client, node_id)

        future = client.send(node_id, request)
        client.poll(future=future)  # block until we get response.
        assert future.succeeded()
        response = future.value

        return response

    def _get_group_coordinator(self, client, group):
        request = GroupCoordinatorRequest[0](group)

        # not all brokers might return a good response... Try all of them
        coord_id = None
        for _ in range(self._broker_retries):
            for broker in client.cluster.brokers():
                try:
                    coord_resp = self._make_blocking_req(client, request, node_id=broker.nodeId)
                    # 0 means that there is no error
                    if coord_resp and coord_resp.error_code is 0:
                        client.cluster.add_group_coordinator(group, coord_resp)
                        coord_id = client.cluster.coordinator_for_group(group)
                        if coord_id is not None and coord_id >= 0:
                            return coord_id
                except AssertionError:
                    continue
            else:
                coord_id = None

        return coord_id

    def _process_highwater_offsets(self, request, instance, node_id, response):
        highwater_offsets = {}
        topic_partitions_without_a_leader = []

        for tp in response.topics:
            topic = tp[0]
            partitions = tp[1]
            for partition, error_code, offsets in partitions:
                if error_code == KAFKA_NO_ERROR:
                    highwater_offsets[(topic, partition)] = offsets[0]
                    # Valid error codes:
                    # https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-PossibleErrorCodes.2
                elif error_code == KAFKA_UNKNOWN_ERROR:
                    self.log.error("Kafka broker returned UNKNOWN (error_code -1) for topic: %s, partition: %s. "
                                   "This should never happen.", topic, partition)
                elif error_code == KAFKA_UNKNOWN_TOPIC_OR_PARTITION:
                    self.log.warn("Kafka broker returned UNKNOWN_TOPIC_OR_PARTITION (error_code 3) for "
                                  "topic: %s, partition: %s. This should only happen if the topic is "
                                  "currently being deleted.",
                                  topic, partition)
                elif error_code == KAFKA_NOT_LEADER_FOR_PARTITION:
                    self.log.warn("Kafka broker returned NOT_LEADER_FOR_PARTITION (error_code 6) for "
                                  "topic: %s, partition: %s. This should only happen if the broker that "
                                  "was the partition leader when kafka_client.cluster last fetched metadata "
                                  "is no longer the leader.", topic, partition)
                    topic_partitions_without_a_leader.append((topic, partition))

        return highwater_offsets, topic_partitions_without_a_leader

    def _get_broker_offsets(self, instance, topics):
        """
        Fetch highwater offsets for each topic/partition from Kafka cluster.

        Do this for all partitions in the cluster because even if it has no
        consumers, we may want to measure whether producers are successfully
        producing. No need to limit this for performance because fetching broker
        offsets from Kafka is a relatively inexpensive operation.

        Sends one OffsetRequest per broker to get offsets for all partitions
        where that broker is the leader:
        https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetAPI(AKAListOffset)

        Can we cleanup connections on agent restart?
        Brokers before 0.9 - accumulate stale connections on restarts.
        In 0.9 Kafka added connections.max.idle.ms
        https://issues.apache.org/jira/browse/KAFKA-1282
        """

        # Connect to Kafka
        highwater_offsets = {}
        topic_partitions_without_a_leader = []
        topics_to_fetch = defaultdict(set)
        cli = self._get_kafka_client(instance)

        for topic, partitions in topics.iteritems():
            # if no partitions are provided
            # we're falling back to all available partitions (?)
            if len(partitions) == 0:
                partitions = cli.cluster.available_partitions_for_topic(topic)
            topics_to_fetch[topic].update(partitions)

        leader_tp = defaultdict(lambda: defaultdict(set))
        for topic, partitions in topics_to_fetch.iteritems():
            for partition in partitions:
                partition_leader = cli.cluster.leader_for_partition(TopicPartition(topic, partition))
                if partition_leader is not None and partition_leader >= 0:
                    leader_tp[partition_leader][topic].update([partition])

        max_offsets = 1
        for node_id, tps in leader_tp.iteritems():
            # Construct the OffsetRequest
            request = OffsetRequest[0](
                replica_id=-1,
                topics=[
                    (topic, [
                        (partition, OffsetResetStrategy.LATEST, max_offsets) for partition in partitions])
                    for topic, partitions in tps.iteritems()])

            response = self._make_blocking_req(cli, request, node_id=node_id)
            offsets, unled = self._process_highwater_offsets(request, instance, node_id, response)
            highwater_offsets.update(offsets)
            topic_partitions_without_a_leader.extend(unled)

        return highwater_offsets, list(set(topic_partitions_without_a_leader))

    def _report_consumer_metrics(self, highwater_offsets, consumer_offsets, unled_topic_partitions=None, tags=None):
        if unled_topic_partitions is None:
            unled_topic_partitions = []
        if tags is None:
            tags = []
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.iteritems():
            # Report the consumer group offsets and consumer lag
            if (topic, partition) not in highwater_offsets:
                self.log.warn("[%s] topic: %s partition: %s was not available in the consumer "
                              "- skipping consumer submission", consumer_group, topic, partition)
                if (topic, partition) not in unled_topic_partitions:
                    self.log.warn("Consumer group: %s has offsets for topic: %s "
                                  "partition: %s, but that topic partition doesn't actually "
                                  "exist in the cluster.", consumer_group, topic, partition)
                continue

            consumer_group_tags = ['topic:%s' % topic, 'partition:%s' % partition,
                                   'consumer_group:%s' % consumer_group] + tags
            self.gauge('kafka.consumer_offset', consumer_offset, tags=consumer_group_tags)

            consumer_lag = highwater_offsets[(topic, partition)] - consumer_offset
            if consumer_lag < 0:
                # this will result in data loss, so emit an event for max visibility
                title = "Negative consumer lag for group: {group}.".format(group=consumer_group)
                message = "Consumer lag for consumer group: {group}, topic: {topic}, " \
                    "partition: {partition} is negative. This should never happen.".format(
                        group=consumer_group,
                        topic=topic,
                        partition=partition
                    )
                key = "{}:{}:{}".format(consumer_group, topic, partition)
                self._send_event(title, message, consumer_group_tags, 'consumer_lag',
                                 key, severity="error")
                self.log.debug(message)

            self.gauge('kafka.consumer_lag', consumer_lag, tags=consumer_group_tags)

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

    def _get_zk_consumer_offsets(self, zk_hosts_ports, consumer_groups=None, zk_prefix=''):
        """
        Fetch Consumer Group offsets from Zookeeper.

        Also fetch consumer_groups, topics, and partitions if not
        already specified in consumer_groups.

        :param dict consumer_groups: The consumer groups, topics, and partitions
            that you want to fetch offsets for. If consumer_groups is None, will
            fetch offsets for all consumer_groups. For examples of what this
            dict can look like, see _validate_explicit_consumer_groups().
        """
        zk_consumer_offsets = {}

        # Construct the Zookeeper path pattern
        # /consumers/[groupId]/offsets/[topic]/[partitionId]
        zk_path_consumer = zk_prefix + '/consumers/'
        zk_path_topic_tmpl = zk_path_consumer + '{group}/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '{topic}/'

        zk_conn = KazooClient(zk_hosts_ports, timeout=self._zk_timeout)
        zk_conn.start()
        try:
            if consumer_groups is None:
                # If consumer groups aren't specified, fetch them from ZK
                consumer_groups = {consumer_group: None for consumer_group in
                                   self._get_zk_path_children(zk_conn, zk_path_consumer, 'consumer groups')}

            for consumer_group, topics in consumer_groups.iteritems():
                if topics is None:
                    # If topics are't specified, fetch them from ZK
                    zk_path_topics = zk_path_topic_tmpl.format(group=consumer_group)
                    topics = {topic: None for topic in
                              self._get_zk_path_children(zk_conn, zk_path_topics, 'topics')}
                    consumer_groups[consumer_group] = topics

                for topic, partitions in topics.iteritems():
                    if partitions is not None:
                        partitions = set(partitions)  # defend against bad user input
                    else:
                        # If partitions aren't specified, fetch them from ZK
                        zk_path_partitions = zk_path_partition_tmpl.format(
                            group=consumer_group, topic=topic)
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
                            zk_consumer_offsets[key] = consumer_offset
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
        return zk_consumer_offsets, consumer_groups

    def _get_kafka_consumer_offsets(self, instance, consumer_groups):
        """
        retrieve consumer offsets via the new consumer api. Offsets in this version are stored directly
        in kafka (__consumer_offsets topic) rather than in zookeeper
        """
        consumer_offsets = {}
        topics = defaultdict(set)

        cli = self._get_kafka_client(instance)

        for consumer_group, topic_partitions in consumer_groups.iteritems():
            try:
                coordinator_id = self._get_group_coordinator(cli, consumer_group)
                if coordinator_id:
                    offsets = self._get_consumer_offsets(cli, consumer_group, topic_partitions, coordinator_id)
                else:
                    offsets = self._get_consumer_offsets(cli, consumer_group, topic_partitions)
                    self.log.info("unable to find group coordinator for %s", consumer_group)

                for (topic, partition), offset in offsets.iteritems():
                    topics[topic].update([partition])
                    key = (consumer_group, topic, partition)
                    consumer_offsets[key] = offset
            except Exception:
                self.log.exception('Could not read consumer offsets from kafka.')

        return consumer_offsets, topics

    def _get_consumer_offsets(self, client, consumer_group, topic_partitions, coord_id=None):
        tps = defaultdict(set)
        for topic, partitions in topic_partitions.iteritems():
            if len(partitions) == 0:
                partitions = client.cluster.available_partitions_for_topic(topic)
            tps[topic] = tps[unicode(topic)].union(set(partitions))

        consumer_offsets = {}
        if coord_id is not None and coord_id >= 0:
            broker_ids = [coord_id]
        else:
            broker_ids = [b.nodeId for b in client.cluster.brokers()]

        for broker_id in broker_ids:
            # Kafka protocol uses OffsetFetchRequests to retrieve consumer offsets:
            # https://kafka.apache.org/protocol#The_Messages_OffsetFetch
            # https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetFetchRequest
            request = OffsetFetchRequest[1](consumer_group, list(tps.iteritems()))
            response = self._make_blocking_req(client, request, node_id=broker_id)
            for (topic, partition_offsets) in response.topics:
                for partition, offset, _, error_code in partition_offsets:
                    if error_code is not 0:
                        continue
                    consumer_offsets[(topic, partition)] = offset

        return consumer_offsets

    def _should_zk(self, zk_hosts_ports, interval, kafka_collect=False):
        if not kafka_collect or not interval:
            return True

        now = time()
        last = self._zk_last_ts.get(zk_hosts_ports, 0)

        should_zk = False
        if (now-last) >= interval:
            self._zk_last_ts[zk_hosts_ports] = last
            should_zk = True

        return should_zk

    def _validate_explicit_consumer_groups(self, val):
        """Validate any explicitly specified consumer groups.

        While the check does not require specifying consumer groups,
        if they are specified this method should be used to validate them.

        val = {'consumer_group': {'topic': [0, 1]}}
        """
        assert isinstance(val, dict)
        for consumer_group, topics in val.iteritems():
            assert isinstance(consumer_group, basestring)
            # topics are optional
            assert isinstance(topics, dict) or topics is None
            if topics is not None:
                for topic, partitions in topics.iteritems():
                    assert isinstance(topic, basestring)
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
