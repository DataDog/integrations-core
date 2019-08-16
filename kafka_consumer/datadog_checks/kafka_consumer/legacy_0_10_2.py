# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

from collections import defaultdict
from time import time

from kafka import errors as kafka_errors
from kafka.client import KafkaClient
from kafka.protocol.commit import GroupCoordinatorRequest, OffsetFetchRequest
from kafka.protocol.offset import OffsetRequest, OffsetResetStrategy
from kafka.structs import TopicPartition
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError
from six import string_types

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .constants import CONTEXT_UPPER_BOUND, DEFAULT_KAFKA_TIMEOUT


class LegacyKafkaCheck_0_10_2(AgentCheck):
    """
    Check the offsets and lag of Kafka consumers. This check also returns broker highwater offsets.

    This is the legacy codepath which is used when either broker version < 0.10.2 or zk_connect_str has a value.
    """

    __NAMESPACE__ = 'kafka'

    def __init__(self, name, init_config, instances):
        super(LegacyKafkaCheck_0_10_2, self).__init__(name, init_config, instances)
        self._context_limit = int(init_config.get('max_partition_contexts', CONTEXT_UPPER_BOUND))
        self._custom_tags = self.instance.get('tags', [])
        self._kafka_client = self._create_kafka_client()
        self._zk_hosts_ports = self.instance.get('zk_connect_str')

        # If we are collecting from Zookeeper, then create a long-lived zk client
        if self._zk_hosts_ports is not None:

            # any chroot prefix gets appended onto the host string or the last item on the host list
            chroot = self.instance.get('zk_prefix')
            if chroot is not None:
                if isinstance(self._zk_hosts_ports, string_types):
                    self._zk_hosts_ports += chroot
                elif isinstance(self._zk_hosts_ports, list):
                    self._zk_hosts_ports.append(chroot)
                else:
                    raise ConfigurationError("zk_connect_str must be a string or list of strings")

            self._zk_client = KazooClient(hosts=self._zk_hosts_ports, timeout=int(init_config.get('zk_timeout', 5)))
            self._zk_client.start()

    def check(self, instance):
        # For calculating consumer lag, we have to fetch both the consumer offset and the broker highwater offset.
        # There's a potential race condition because whichever one we check first may be outdated by the time we check
        # the other. Better to check consumer offsets before checking broker offsets because worst case is that
        # overstates consumer lag a little. Doing it the other way can understate consumer lag to the point of having
        # negative consumer lag, which just creates confusion because it's theoretically impossible.

        # If monitor_unlisted_consumer_groups is True, fetch all groups stored in ZK
        consumer_groups = None
        if instance.get('monitor_unlisted_consumer_groups', False):
            consumer_groups = None
        elif 'consumer_groups' in instance:
            consumer_groups = instance.get('consumer_groups')
            self._validate_explicit_consumer_groups(consumer_groups)

        # Fetch consumer group offsets from Zookeeper
        zk_consumer_offsets = None
        if self._zk_hosts_ports is not None:
            zk_consumer_offsets, consumer_groups = self._get_zk_consumer_offsets(consumer_groups)

        topics = defaultdict(set)

        kafka_consumer_offsets = None

        # Fetch consumer group offsets from Kafka

        # For legacy reasons, this only fetches consumer offsets from kafka if zookeeper is omitted or
        # kafka_consumer_offsets is True.
        if is_affirmative(instance.get('kafka_consumer_offsets', self._zk_hosts_ports is None)):
            # For now, consumer groups are mandatory if not using ZK
            if self._zk_hosts_ports is None and not consumer_groups:
                raise ConfigurationError(
                    'Invalid configuration - if you are collecting consumer offsets from Kafka, and your brokers are '
                    'older than 0.10.2, then you _must_ specify consumer groups and their topics. Older brokers lack '
                    'the necessary protocol support to determine which topics a consumer is consuming. See KIP-88 for '
                    'details.'
                )
            # Kafka 0.8.2 added support for storing consumer offsets in Kafka.
            if self._kafka_client.config.get('api_version') >= (0, 8, 2):
                kafka_consumer_offsets, topics = self._get_kafka_consumer_offsets(instance, consumer_groups)

        if not topics:
            # val = {'consumer_group': {'topic': [0, 1]}}
            for _, tps in consumer_groups.items():
                for topic, partitions in tps.items():
                    topics[topic].update(partitions)

        warn_msg = """ Discovered %s partition contexts - this exceeds the maximum
                       number of contexts permitted by the check. Please narrow your
                       target by specifying in your YAML what consumer groups, topics
                       and partitions you wish to monitor."""
        if zk_consumer_offsets and len(zk_consumer_offsets) > self._context_limit:
            self.warning(warn_msg % len(zk_consumer_offsets))
            return
        if kafka_consumer_offsets and len(kafka_consumer_offsets) > self._context_limit:
            self.warning(warn_msg % len(kafka_consumer_offsets))
            return

        # Fetch the broker highwater offsets
        try:
            highwater_offsets = self._get_broker_offsets(topics)
        except Exception:
            self.log.exception('There was a problem collecting the high watermark offsets')
            return

        # Report the broker highwater offset
        for (topic, partition), highwater_offset in highwater_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            broker_tags.extend(self._custom_tags)
            self.gauge('broker_offset', highwater_offset, tags=broker_tags)

        # Report the consumer group offsets and consumer lag
        if zk_consumer_offsets:
            self._report_consumer_metrics(highwater_offsets, zk_consumer_offsets, 'zk')
        if kafka_consumer_offsets:
            self._report_consumer_metrics(highwater_offsets, kafka_consumer_offsets, 'kafka')

    def _create_kafka_client(self):
        kafka_conn_str = self.instance.get('kafka_connect_str')
        if not isinstance(kafka_conn_str, (string_types, list)):
            raise ConfigurationError('kafka_connect_str should be string or list of strings')
        return KafkaClient(
            bootstrap_servers=kafka_conn_str,
            client_id='dd-agent',
            request_timeout_ms=self.init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT) * 1000,
            # if `kafka_client_api_version` is not set, then kafka-python automatically probes the cluster for broker
            # version during the bootstrapping process. Note that probing randomly picks a broker to probe, so in a
            # mixed-version cluster probing returns a non-deterministic result.
            api_version=self.instance.get('kafka_client_api_version'),
            # While we check for SSL params, if not present they will default to the kafka-python values for plaintext
            # connections
            security_protocol=self.instance.get('security_protocol', 'PLAINTEXT'),
            sasl_mechanism=self.instance.get('sasl_mechanism'),
            sasl_plain_username=self.instance.get('sasl_plain_username'),
            sasl_plain_password=self.instance.get('sasl_plain_password'),
            sasl_kerberos_service_name=self.instance.get('sasl_kerberos_service_name', 'kafka'),
            sasl_kerberos_domain_name=self.instance.get('sasl_kerberos_domain_name'),
            ssl_cafile=self.instance.get('ssl_cafile'),
            ssl_check_hostname=self.instance.get('ssl_check_hostname', True),
            ssl_certfile=self.instance.get('ssl_certfile'),
            ssl_keyfile=self.instance.get('ssl_keyfile'),
            ssl_crlfile=self.instance.get('ssl_crlfile'),
            ssl_password=self.instance.get('ssl_password'),
        )

    def _make_blocking_req(self, request, node_id=None):
        if node_id is None:
            node_id = self._kafka_client.least_loaded_node()

        while not self._kafka_client.ready(node_id):
            # poll until the connection to broker is ready, otherwise send() will fail with NodeNotReadyError
            self._kafka_client.poll()

        future = self._kafka_client.send(node_id, request)
        self._kafka_client.poll(future=future)  # block until we get response.
        assert future.succeeded()
        response = future.value
        return response

    def _process_highwater_offsets(self, response):
        highwater_offsets = {}

        for tp in response.topics:
            topic = tp[0]
            partitions = tp[1]
            for partition, error_code, offsets in partitions:
                error_type = kafka_errors.for_code(error_code)
                if error_type is kafka_errors.NoError:
                    highwater_offsets[(topic, partition)] = offsets[0]
                    # Valid error codes:
                    # https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-PossibleErrorCodes.2
                elif error_type is kafka_errors.NotLeaderForPartitionError:
                    self.log.warn(
                        "Kafka broker returned %s (error_code %s) for topic %s, partition: %s. This should only happen "
                        "if the broker that was the partition leader when kafka_admin_client last fetched metadata is "
                        "no longer the leader.",
                        error_type.message,
                        error_type.errno,
                        topic,
                        partition,
                    )
                    self._kafka_client.cluster.request_update()  # force metadata update on next poll()
                elif error_type is kafka_errors.UnknownTopicOrPartitionError:
                    self.log.warn(
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

        return highwater_offsets

    def _get_broker_offsets(self, topics):
        """
        Fetch highwater offsets for topic_partitions in the Kafka cluster.

        Do this for all partitions in the cluster because even if it has no consumers, we may want to measure whether
        producers are successfully producing.

        Sends one OffsetRequest per broker to get offsets for all partitions where that broker is the leader:
        https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetAPI(AKAListOffset)
        """

        # Connect to Kafka
        highwater_offsets = {}
        topics_to_fetch = defaultdict(set)

        for topic, partitions in topics.items():
            # if no partitions are provided
            # we're falling back to all available partitions (?)
            if len(partitions) == 0:
                partitions = self._kafka_client.cluster.available_partitions_for_topic(topic)
            topics_to_fetch[topic].update(partitions)

        leader_tp = defaultdict(lambda: defaultdict(set))
        for topic, partitions in topics_to_fetch.items():
            for partition in partitions:
                partition_leader = self._kafka_client.cluster.leader_for_partition(TopicPartition(topic, partition))
                if partition_leader is not None and partition_leader >= 0:
                    leader_tp[partition_leader][topic].add(partition)

        max_offsets = 1
        for node_id, tps in leader_tp.items():
            # Construct the OffsetRequest
            request = OffsetRequest[0](
                replica_id=-1,
                topics=[
                    (topic, [(partition, OffsetResetStrategy.LATEST, max_offsets) for partition in partitions])
                    for topic, partitions in tps.items()
                ],
            )

            response = self._make_blocking_req(request, node_id=node_id)
            offsets = self._process_highwater_offsets(response)
            highwater_offsets.update(offsets)
        return highwater_offsets

    def _report_consumer_metrics(self, highwater_offsets, consumer_offsets, consumer_offsets_source):
        """Report the consumer group offsets and consumer lag."""
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.items():
            consumer_group_tags = [
                'topic:%s' % topic,
                'partition:%s' % partition,
                'consumer_group:%s' % consumer_group,
                'source:%s' % consumer_offsets_source,
            ]
            consumer_group_tags.extend(self._custom_tags)
            if partition in self._kafka_client.cluster.partitions_for_topic(topic):
                # report consumer offset if the partition is valid because even if leaderless the consumer offset will
                # be valid once the leader failover completes
                self.gauge('consumer_offset', consumer_offset, tags=consumer_group_tags)
                if (topic, partition) not in highwater_offsets:
                    self.log.warn(
                        "Consumer group: %s has offsets for topic: %s partition: %s, but no stored highwater offset "
                        "(likely the partition is in the middle of leader failover) so cannot calculate consumer lag.",
                        consumer_group,
                        topic,
                        partition,
                    )
                    continue

                consumer_lag = highwater_offsets[(topic, partition)] - consumer_offset
                self.gauge('consumer_lag', consumer_lag, tags=consumer_group_tags)

                if consumer_lag < 0:  # this will effectively result in data loss, so emit an event for max visibility
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
                self.log.warn(
                    "Consumer group: %s has offsets for topic: %s, partition: %s, but that topic partition doesn't "
                    "appear to exist in the cluster so skipping reporting these offsets.",
                    consumer_group,
                    topic,
                    partition,
                )
                self._kafka_client.cluster.request_update()  # force metadata update on next poll()

    def _get_zk_path_children(self, zk_path, name_for_error):
        """Fetch child nodes for a given Zookeeper path."""
        children = []
        try:
            children = self._zk_client.get_children(zk_path)
        except NoNodeError:
            self.log.info('No zookeeper node at %s', zk_path)
        except Exception:
            self.log.exception('Could not read %s from %s', name_for_error, zk_path)
        return children

    def _get_zk_consumer_offsets(self, consumer_groups=None):
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
        zk_path_consumer = '/consumers/'
        zk_path_topic_tmpl = zk_path_consumer + '{group}/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '{topic}/'

        if consumer_groups is None:
            # If consumer groups aren't specified, fetch them from ZK
            consumer_groups = {
                consumer_group: None
                for consumer_group in self._get_zk_path_children(zk_path_consumer, 'consumer groups')
            }

        for consumer_group, topics in consumer_groups.items():
            if not topics:
                # If topics are't specified, fetch them from ZK
                zk_path_topics = zk_path_topic_tmpl.format(group=consumer_group)
                topics = {topic: None for topic in self._get_zk_path_children(zk_path_topics, 'topics')}
                consumer_groups[consumer_group] = topics

            for topic, partitions in topics.items():
                if partitions:
                    partitions = set(partitions)  # defend against bad user input
                else:
                    # If partitions aren't specified, fetch them from ZK
                    zk_path_partitions = zk_path_partition_tmpl.format(group=consumer_group, topic=topic)
                    # Zookeeper returns the partition IDs as strings because
                    # they are extracted from the node path
                    partitions = [int(x) for x in self._get_zk_path_children(zk_path_partitions, 'partitions')]
                    consumer_groups[consumer_group][topic] = partitions

                # Fetch consumer offsets for each partition from ZK
                for partition in partitions:
                    zk_path = (zk_path_partition_tmpl + '{partition}/').format(
                        group=consumer_group, topic=topic, partition=partition
                    )
                    try:
                        consumer_offset = int(self._zk_client.get(zk_path)[0])
                        key = (consumer_group, topic, partition)
                        zk_consumer_offsets[key] = consumer_offset
                    except NoNodeError:
                        self.log.info('No zookeeper node at %s', zk_path)
                    except Exception:
                        self.log.exception('Could not read consumer offset from %s', zk_path)
        return zk_consumer_offsets, consumer_groups

    def _get_kafka_consumer_offsets(self, instance, consumer_groups):
        """
        Get offsets for all consumer groups from Kafka.

        These offsets are stored in the __consumer_offsets topic rather than in Zookeeper.
        """
        consumer_offsets = {}
        topics = defaultdict(set)

        for consumer_group, topic_partitions in consumer_groups.items():
            try:
                single_group_offsets = self._get_single_group_offsets_from_kafka(consumer_group, topic_partitions)
                for (topic, partition), offset in single_group_offsets.items():
                    topics[topic].update([partition])
                    key = (consumer_group, topic, partition)
                    consumer_offsets[key] = offset
            except Exception:
                self.log.exception('Could not read consumer offsets from kafka for group: ' % consumer_group)

        return consumer_offsets, topics

    def _get_group_coordinator(self, group):
        """Determine which broker is the Group Coordinator for a specific consumer group."""
        request = GroupCoordinatorRequest[0](group)
        response = self._make_blocking_req(request)
        error_type = kafka_errors.for_code(response.error_code)
        if error_type is kafka_errors.NoError:
            return response.coordinator_id

    def _get_single_group_offsets_from_kafka(self, consumer_group, topic_partitions):
        """Get offsets for a single consumer group from Kafka"""
        consumer_offsets = {}
        tps = defaultdict(set)
        for topic, partitions in topic_partitions.items():
            if len(partitions) == 0:
                # If partitions omitted, then we assume the group is consuming all partitions for the topic.
                # Fetch consumer offsets even for unavailable partitions because those will be valid once the partition
                # finishes leader failover.
                partitions = self._kafka_client.cluster.partitions_for_topic(topic)
            tps[topic].update(partitions)

        coordinator_id = self._get_group_coordinator(consumer_group)
        if coordinator_id is not None:
            # Kafka protocol uses OffsetFetchRequests to retrieve consumer offsets:
            # https://kafka.apache.org/protocol#The_Messages_OffsetFetch
            # https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetFetchRequest
            request = OffsetFetchRequest[1](consumer_group, tps.items())
            response = self._make_blocking_req(request, node_id=coordinator_id)
            for (topic, partition_offsets) in response.topics:
                for partition, offset, _, error_code in partition_offsets:
                    error_type = kafka_errors.for_code(error_code)
                    if error_type is not kafka_errors.NoError:
                        continue
                    consumer_offsets[(topic, partition)] = offset
        else:
            self.log.info("unable to find group coordinator for %s", consumer_group)

        return consumer_offsets

    @classmethod
    def _validate_explicit_consumer_groups(cls, val):
        """Validate any explicitly specified consumer groups.

        While the check does not require specifying consumer groups,
        if they are specified this method should be used to validate them.

        val = {'consumer_group': {'topic': [0, 1]}}
        """
        assert isinstance(val, dict)
        for consumer_group, topics in val.items():
            assert isinstance(consumer_group, string_types)
            # topics are optional
            assert isinstance(topics, dict) or topics is None
            if topics is not None:
                for topic, partitions in topics.items():
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
            'msg_title': title,
            'event_type': event_type,
            'alert_type': severity,
            'msg_text': text,
            'tags': tags,
            'aggregation_key': aggregation_key,
        }
        self.event(event_dict)
