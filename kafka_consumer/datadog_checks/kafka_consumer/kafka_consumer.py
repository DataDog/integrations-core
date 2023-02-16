# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from time import time

from datadog_checks.base import AgentCheck
from datadog_checks.kafka_consumer.client.kafka_client_factory import make_client
from datadog_checks.kafka_consumer.config import KafkaConfig


class KafkaCheck(AgentCheck):

    __NAMESPACE__ = 'kafka'

    # This remapper is used to support legacy config values
    TLS_CONFIG_REMAPPER = {
        'ssl_check_hostname': {'name': 'tls_validate_hostname'},
        'ssl_cafile': {'name': 'tls_ca_cert'},
        'ssl_certfile': {'name': 'tls_cert'},
        'ssl_keyfile': {'name': 'tls_private_key'},
        'ssl_password': {'name': 'tls_private_key_password'},
    }

    def __init__(self, name, init_config, instances):
        super(KafkaCheck, self).__init__(name, init_config, instances)
        self.config = KafkaConfig(self.init_config, self.instance)
        self._context_limit = self.config._context_limit
        tls_context = self.get_tls_context()
        self.client = make_client(self, self.config, tls_context)

    def check(self, _):
        """The main entrypoint of the check."""
        # Fetch Kafka consumer offsets
        self.client.reset_offsets()

        try:
            self.client.get_consumer_offsets()
        except Exception:
            self.log.exception("There was a problem collecting consumer offsets from Kafka.")
            # don't raise because we might get valid broker offsets

        # Fetch the broker highwater offsets
        try:
            if self.client.should_get_highwater_offsets():
                self.client.get_highwater_offsets()
            else:
                self.warning("Context limit reached. Skipping highwater offset collection.")
        except Exception:
            self.log.exception("There was a problem collecting the highwater mark offsets.")
            # Unlike consumer offsets, fail immediately because we can't calculate consumer lag w/o highwater_offsets
            raise

        total_contexts = len(self.client._consumer_offsets) + len(self.client._highwater_offsets)
        if total_contexts >= self._context_limit:
            self.warning(
                """Discovered %s metric contexts - this exceeds the maximum number of %s contexts permitted by the
                check. Please narrow your target by specifying in your kafka_consumer.yaml the consumer groups, topics
                and partitions you wish to monitor.""",
                total_contexts,
                self._context_limit,
            )

        # Report the metrics
        # Expected format: {(consumer_group, topic, partition): offset}
        self._consumer_offsets = self.client.get_consumer_offsets_dict()
        # Expected format: {(topic, partition): offset}
        self._highwater_offsets = self.client.get_highwater_offsets_dict()

        self.report_highwater_offsets(self._context_limit)
        self.report_consumer_offsets_and_lag(self._context_limit - len(self._highwater_offsets))

        self.collect_broker_metadata()

    def report_highwater_offsets(self, contexts_limit):
        """Report the broker highwater offsets."""
        reported_contexts = 0
        self.log.debug("Reporting broker offset metric")
        for (topic, partition), highwater_offset in self._highwater_offsets.items():
            broker_tags = ['topic:%s' % topic, 'partition:%s' % partition]
            broker_tags.extend(self.config._custom_tags)
            self.gauge('broker_offset', highwater_offset, tags=broker_tags)
            reported_contexts += 1
            if reported_contexts == contexts_limit:
                return

    def report_consumer_offsets_and_lag(self, contexts_limit):
        """Report the consumer offsets and consumer lag."""
        reported_contexts = 0
        self.log.debug("Reporting consumer offsets and lag metrics")
        for (consumer_group, topic, partition), consumer_offset in self._consumer_offsets.items():
            if reported_contexts >= contexts_limit:
                self.log.debug(
                    "Reported contexts number %s greater than or equal to contexts limit of %s, returning",
                    str(reported_contexts),
                    str(contexts_limit),
                )
                return
            consumer_group_tags = ['topic:%s' % topic, 'partition:%s' % partition, 'consumer_group:%s' % consumer_group]
            consumer_group_tags.extend(self.config._custom_tags)

            partitions = self.client.get_partitions_for_topic(topic)
            self.log.debug("Received partitions %s for topic %s", partitions, topic)
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
                self.client.request_metadata_update()  # force metadata update on next poll()

    @AgentCheck.metadata_entrypoint
    def collect_broker_metadata(self):
        version_data = [str(part) for part in self.client.collect_broker_version()]
        version_parts = {name: part for name, part in zip(('major', 'minor', 'patch'), version_data)}

        self.set_metadata(
            'version', '.'.join(version_data), scheme='parts', final_scheme='semver', part_map=version_parts
        )

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
