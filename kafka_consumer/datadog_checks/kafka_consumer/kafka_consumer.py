# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.kafka_consumer.client.kafka_client_factory import make_client

from .constants import BROKER_REQUESTS_BATCH_SIZE, CONTEXT_UPPER_BOUND


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
        self._context_limit = int(self.init_config.get('max_partition_contexts', CONTEXT_UPPER_BOUND))
        self._custom_tags = self.instance.get('tags', [])
        self._monitor_unlisted_consumer_groups = is_affirmative(
            self.instance.get('monitor_unlisted_consumer_groups', False)
        )
        self._monitor_all_broker_highwatermarks = is_affirmative(
            self.instance.get('monitor_all_broker_highwatermarks', False)
        )
        self._consumer_groups = self.instance.get('consumer_groups', {})
        self._broker_requests_batch_size = self.instance.get('broker_requests_batch_size', BROKER_REQUESTS_BATCH_SIZE)
        self.client = make_client(self)

    def check(self, _):
        """The main entrypoint of the check."""
        self._consumer_offsets = {}  # Expected format: {(consumer_group, topic, partition): offset}
        self._highwater_offsets = {}  # Expected format: {(topic, partition): offset}

        # Fetch Kafka consumer offsets
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
        self.client.report_highwater_offsets(self._context_limit)
        self.client.report_consumer_offsets_and_lag(self._context_limit - len(self.client._highwater_offsets))

        self.collect_broker_metadata()

    @AgentCheck.metadata_entrypoint
    def collect_broker_metadata(self):
        self.client.collect_broker_metadata()

    # TODO: Remove me once the tests are refactored
    def send_event(self, title, text, tags, event_type, aggregation_key, severity='info'):
        self.client._send_event(title, text, tags, event_type, aggregation_key, severity='info')
