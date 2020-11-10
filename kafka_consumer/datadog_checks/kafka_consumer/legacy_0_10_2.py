# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

from collections import defaultdict
from time import time

from kafka import KafkaClient
from kafka import errors as kafka_errors
from kafka.protocol.commit import GroupCoordinatorRequest, OffsetFetchRequest
from kafka.protocol.offset import OffsetRequest, OffsetResetStrategy, OffsetResponse
from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError
from six import string_types

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .constants import CONTEXT_UPPER_BOUND, DEFAULT_KAFKA_TIMEOUT, KAFKA_INTERNAL_TOPICS


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

        self._monitor_unlisted_consumer_groups = is_affirmative(
            self.instance.get('monitor_unlisted_consumer_groups', False)
        )
        self._monitor_all_broker_highwatermarks = is_affirmative(
            self.instance.get('monitor_all_broker_highwatermarks', False)
        )
        self._consumer_groups = self.instance.get('consumer_groups', {})
        # Note: We cannot skip validation if monitor_unlisted_consumer_groups is True because this legacy check only
        # supports that functionality for Zookeeper, not Kafka.
        self._validate_explicit_consumer_groups()

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

    def check(self, _):
        """The main entrypoint of the check."""
        self.log.debug("Running legacy Kafka Consumer check.")
        self._zk_consumer_offsets = {}  # Expected format: {(consumer_group, topic, partition): offset}
        self._kafka_consumer_offsets = {}  # Expected format: {(consumer_group, topic, partition): offset}
        self._highwater_offsets = {}  # Expected format: {(topic, partition): offset}
        contexts_limit = self._context_limit

        # For calculating consumer lag, we have to fetch both the consumer offset and the broker highwater offset.
        # There's a potential race condition because whichever one we check first may be outdated by the time we check
        # the other. Better to check consumer offsets before checking broker offsets because worst case is that
        # overstates consumer lag a little. Doing it the other way can understate consumer lag to the point of having
        # negative consumer lag, which just creates confusion because it's theoretically impossible.

        # Fetch consumer group offsets from Zookeeper
        if self._zk_hosts_ports is not None:
            try:
                self._get_zk_consumer_offsets(contexts_limit)
                contexts_limit -= len(self._zk_consumer_offsets)
            except Exception:
                self.log.exception("There was a problem collecting consumer offsets from Zookeeper.")
                # don't raise because we might get valid broker offsets

        # Fetch consumer group offsets from Kafka
        # Support for storing offsets in Kafka not available until Kafka 0.8.2. Also, for legacy reasons, this check
        # only fetches consumer offsets from Kafka if Zookeeper is omitted or kafka_consumer_offsets is True.
        if self._kafka_client.config.get('api_version') >= (0, 8, 2) and is_affirmative(
            self.instance.get('kafka_consumer_offsets', self._zk_hosts_ports is None)
        ):
            try:
                self._get_kafka_consumer_offsets(contexts_limit)
                contexts_limit -= len(self._kafka_consumer_offsets)
            except Exception:
                self.log.exception("There was a problem collecting consumer offsets from Kafka.")
                # don't raise because we might get valid broker offsets

        # Fetch the broker highwater offsets
        try:
            self._get_highwater_offsets(contexts_limit)
        except Exception:
            self.log.exception('There was a problem collecting the highwater mark offsets')
            # Unlike consumer offsets, fail immediately because we can't calculate consumer lag w/o highwater_offsets
            raise

        total_contexts = sum(
            [len(self._zk_consumer_offsets), len(self._kafka_consumer_offsets), len(self._highwater_offsets)]
        )
        if total_contexts > self._context_limit:
            self.warning(
                """Discovered %s metric contexts - this exceeds the maximum number of %s contexts permitted by the
                check. Please narrow your target by specifying in your kafka_consumer.yaml the consumer groups, topics
                and partitions you wish to monitor.""",
                total_contexts,
                self._context_limit,
            )
        # Report the metrics
        self._report_highwater_offsets()
        self._report_consumer_offsets_and_lag(self._kafka_consumer_offsets)
        # if someone is in the middle of migrating their offset storage from zookeeper to kafka,
        # they need to identify which source is reporting which offsets. So we tag zookeeper with 'source:zk'
        self._report_consumer_offsets_and_lag(self._zk_consumer_offsets, source='zk')

    def _create_kafka_client(self):
        kafka_conn_str = self.instance.get('kafka_connect_str')
        if not isinstance(kafka_conn_str, (string_types, list)):
            raise ConfigurationError('kafka_connect_str should be string or list of strings')
        kafka_version = self.instance.get('kafka_client_api_version')
        if isinstance(kafka_version, str):
            kafka_version = tuple(map(int, kafka_version.split(".")))
        kafka_client = KafkaClient(
            bootstrap_servers=kafka_conn_str,
            client_id='dd-agent',
            request_timeout_ms=self.init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT) * 1000,
            # if `kafka_client_api_version` is not set, then kafka-python automatically probes the cluster for broker
            # version during the bootstrapping process. Note that probing randomly picks a broker to probe, so in a
            # mixed-version cluster probing returns a non-deterministic result.
            api_version=kafka_version,
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
        # Force initial population of the local cluster metadata cache
        kafka_client.poll(future=kafka_client.cluster.request_update())
        if kafka_client.cluster.topics(exclude_internal_topics=False) is None:
            raise RuntimeError("Local cluster metadata cache did not populate.")
        return kafka_client

    def _make_blocking_req(self, request, node_id=None):
        if node_id is None:
            node_id = self._kafka_client.least_loaded_node()

        while not self._kafka_client.ready(node_id):
            # poll until the connection to broker is ready, otherwise send() will fail with NodeNotReadyError
            self._kafka_client.poll()

        future = self._kafka_client.send(node_id, request)
        self._kafka_client.poll(future=future)  # block until we get response.
        if future.failed():
            raise future.exception  # pylint: disable-msg=raising-bad-type
        response = future.value
        return response

    def _get_highwater_offsets(self, contexts_limit):
        """
        Fetch highwater offsets for topic_partitions in the Kafka cluster.

        If monitor_all_broker_highwatermarks is True, will fetch for all partitions in the cluster. Otherwise highwater
        mark offsets will only be fetched for topic partitions where this check run has already fetched a consumer
        offset.

        Internal Kafka topics like __consumer_offsets, __transaction_state, etc are always excluded.

        Any partitions that don't currently have a leader will be skipped.

        Sends one OffsetRequest per broker to get offsets for all partitions where that broker is the leader:
        https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetAPI(AKAListOffset)
        """
        # If we aren't fetching all broker highwater offsets, then construct the unique set of topic partitions for
        # which this run of the check has at least once saved consumer offset. This is later used as a filter for
        # excluding partitions.
        if not self._monitor_all_broker_highwatermarks:
            tps_with_consumer_offset = {(topic, partition) for (_, topic, partition) in self._kafka_consumer_offsets}
            tps_with_consumer_offset.update({(topic, partition) for (_, topic, partition) in self._zk_consumer_offsets})

        for broker in self._kafka_client.cluster.brokers():
            if len(self._highwater_offsets) >= contexts_limit:
                self.log.debug("Context limit reached. Skipping highwater offsets collection.")
                return
            broker_led_partitions = self._kafka_client.cluster.partitions_for_broker(broker.nodeId)
            if broker_led_partitions is None:
                continue
            # Take the partitions for which this broker is the leader and group them by topic in order to construct the
            # OffsetRequest while simultaneously filtering out partitions we want to exclude
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
            response = self._make_blocking_req(request, node_id=broker.nodeId)
            self._process_highwater_offsets(response, contexts_limit)

    def _process_highwater_offsets(self, response, contexts_limit):
        """Parse an OffsetFetchResponse and save it to the highwater_offsets dict."""
        if type(response) not in OffsetResponse:
            raise RuntimeError("response type should be OffsetResponse, but instead was %s." % type(response))
        for topic, partitions_data in response.topics:
            for partition, error_code, offsets in partitions_data:
                error_type = kafka_errors.for_code(error_code)
                if error_type is kafka_errors.NoError:
                    self._highwater_offsets[(topic, partition)] = offsets[0]
                    if len(self._highwater_offsets) >= contexts_limit:
                        self.log.debug("Context limit reached. Skipping highwater offsets processing.")
                        return
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
                    self._kafka_client.cluster.request_update()  # force metadata update on next poll()
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

    def _report_highwater_offsets(self):
        """Report the broker highwater offsets."""
        for (topic, partition), highwater_offset in self._highwater_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            broker_tags.extend(self._custom_tags)
            self.gauge('broker_offset', highwater_offset, tags=broker_tags)

    def _report_consumer_offsets_and_lag(self, consumer_offsets, **kwargs):
        """Report the consumer group offsets and consumer lag."""
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.items():
            consumer_group_tags = ['topic:%s' % topic, 'partition:%s' % partition, 'consumer_group:%s' % consumer_group]
            if 'source' in kwargs:
                consumer_group_tags.append('source:%s' % kwargs['source'])
            consumer_group_tags.extend(self._custom_tags)
            if partition in self._kafka_client.cluster.partitions_for_topic(topic):
                # report consumer offset if the partition is valid because even if leaderless the consumer offset will
                # be valid once the leader failover completes
                self.gauge('consumer_offset', consumer_offset, tags=consumer_group_tags)

                if (topic, partition) not in self._highwater_offsets:
                    self.log.warning(
                        "Consumer group: %s has offsets for topic: %s partition: %s, but no stored highwater offset "
                        "(likely the partition is in the middle of leader failover) so cannot calculate consumer lag.",
                        consumer_group,
                        topic,
                        partition,
                    )
                    continue

                consumer_lag = self._highwater_offsets[(topic, partition)] - consumer_offset
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
                self.log.warning(
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

    def _get_zk_consumer_offsets(self, contexts_limit):
        """
        Fetch Consumer Group offsets from Zookeeper.

        Also fetch consumer_groups, topics, and partitions if not
        already specified in consumer_groups.
        """
        # Construct the Zookeeper path pattern
        # /consumers/[groupId]/offsets/[topic]/[partitionId]
        zk_path_consumer = '/consumers/'
        zk_path_topic_tmpl = zk_path_consumer + '{group}/offsets/'
        zk_path_partition_tmpl = zk_path_topic_tmpl + '{topic}/'

        if self._monitor_unlisted_consumer_groups:
            # don't overwrite self._consumer_groups because that holds the static config values which are always used
            # when fetching consumer offsets from Kafka. Also, these dynamically fetched groups may change on each run.
            consumer_groups = {
                consumer_group: None
                for consumer_group in self._get_zk_path_children(zk_path_consumer, 'consumer groups')
            }
        else:
            consumer_groups = self._consumer_groups

        for consumer_group, topics in consumer_groups.items():
            if not topics:  # If topics are't specified, fetch them from ZK
                zk_path_topics = zk_path_topic_tmpl.format(group=consumer_group)
                topics = {topic: None for topic in self._get_zk_path_children(zk_path_topics, 'topics')}

            for topic, partitions in topics.items():
                if not partitions:  # If partitions aren't specified, fetch them from ZK
                    zk_path_partitions = zk_path_partition_tmpl.format(group=consumer_group, topic=topic)
                    # Zookeeper returns the partition IDs as strings because they are extracted from the node path
                    partitions = [int(x) for x in self._get_zk_path_children(zk_path_partitions, 'partitions')]

                for partition in partitions:
                    zk_path = (zk_path_partition_tmpl + '{partition}/').format(
                        group=consumer_group, topic=topic, partition=partition
                    )
                    try:
                        consumer_offset = int(self._zk_client.get(zk_path)[0])
                        key = (consumer_group, topic, partition)
                        self._zk_consumer_offsets[key] = consumer_offset

                        if len(self._zk_consumer_offsets) >= contexts_limit:
                            self.log.debug("Context limit reached. Skipping zk consumer offsets collection.")
                            return
                    except NoNodeError:
                        self.log.info('No zookeeper node at %s', zk_path)
                        continue
                    except Exception:
                        self.log.exception('Could not read consumer offset from %s', zk_path)

    def _get_kafka_consumer_offsets(self, contexts_limit):
        """
        Fetch Consumer Group offsets from Kafka.

        These offsets are stored in the __consumer_offsets topic rather than in Zookeeper.
        """
        for consumer_group, topic_partitions in self._consumer_groups.items():
            if not topic_partitions:
                raise ConfigurationError(
                    'Invalid configuration - if you are collecting consumer offsets from Kafka, and your brokers are '
                    'older than 0.10.2, then you _must_ specify consumer groups and their topics. Older brokers lack '
                    'the necessary protocol support to determine which topics a consumer is consuming. See KIP-88 for '
                    'details.'
                )
            try:  # catch exceptions on a group-by-group basis so that if one fails we still fetch the other groups
                for topic, partitions in topic_partitions.items():
                    if not partitions:
                        # If partitions omitted, then we assume the group is consuming all partitions for the topic.
                        # Fetch consumer offsets even for unavailable partitions because those will be valid once the
                        # partition finishes leader failover.
                        topic_partitions[topic] = self._kafka_client.cluster.partitions_for_topic(topic)

                coordinator_id = self._get_group_coordinator(consumer_group)
                if coordinator_id is not None:
                    # Kafka protocol uses OffsetFetchRequests to retrieve consumer offsets:
                    # https://kafka.apache.org/protocol#The_Messages_OffsetFetch
                    # https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol#AGuideToTheKafkaProtocol-OffsetFetchRequest
                    request = OffsetFetchRequest[1](consumer_group, list(topic_partitions.items()))
                    response = self._make_blocking_req(request, node_id=coordinator_id)
                    for (topic, partition_offsets) in response.topics:
                        for partition, offset, _metadata, error_code in partition_offsets:
                            error_type = kafka_errors.for_code(error_code)
                            # If the OffsetFetchRequest explicitly specified partitions, the offset could returned as
                            # -1, meaning there is no recorded offset for that partition... for example, if the
                            # partition doesn't exist in the cluster. So ignore it.
                            if offset == -1 or error_type is not kafka_errors.NoError:
                                self._kafka_client.cluster.request_update()  # force metadata update on next poll()
                                continue
                            key = (consumer_group, topic, partition)
                            self._kafka_consumer_offsets[key] = offset

                            if len(self._kafka_consumer_offsets) >= contexts_limit:
                                self.log.debug("Context limit reached. Skipping kafka consumer offsets collection.")
                                return
                else:
                    self.log.info("unable to find group coordinator for %s", consumer_group)
            except Exception:
                self.log.exception('Could not read consumer offsets from Kafka for group: %s', consumer_group)

    def _get_group_coordinator(self, group):
        """Determine which broker is the Group Coordinator for a specific consumer group."""
        request = GroupCoordinatorRequest[0](group)
        response = self._make_blocking_req(request)
        error_type = kafka_errors.for_code(response.error_code)
        if error_type is kafka_errors.NoError:
            return response.coordinator_id

    def _validate_explicit_consumer_groups(self):
        """Validate any explicitly specified consumer groups.

        While the check does not require specifying consumer groups,
        if they are specified this method should be used to validate them.

        consumer_groups = {'consumer_group': {'topic': [0, 1]}}
        """
        assert isinstance(self._consumer_groups, dict)
        for consumer_group, topics in self._consumer_groups.items():
            assert isinstance(consumer_group, string_types)
            assert isinstance(topics, dict) or topics is None  # topics are optional
            if topics is not None:
                for topic, partitions in topics.items():
                    assert isinstance(topic, string_types)
                    assert isinstance(partitions, (list, tuple)) or partitions is None  # partitions are optional
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
