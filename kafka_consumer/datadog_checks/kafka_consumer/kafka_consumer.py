# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import ssl

from kafka import KafkaAdminClient, KafkaClient
from kafka.oauth.abstract import AbstractTokenProvider
from six import string_types

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.http import AuthTokenOAuthReader
from datadog_checks.kafka_consumer.client.kafka_client_factory import make_client

from .constants import BROKER_REQUESTS_BATCH_SIZE, CONTEXT_UPPER_BOUND, DEFAULT_KAFKA_TIMEOUT


class OAuthTokenProvider(AbstractTokenProvider):
    def __init__(self, **config):
        self.reader = AuthTokenOAuthReader(config)

    def token(self):
        # Read only if necessary or use cached token
        return self.reader.read() or self.reader._token


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
        self.client = None

    def create_kafka_client(self):
        return self._create_kafka_client(clazz=KafkaClient)

    def create_kafka_admin_client(self):
        return self._create_kafka_client(clazz=KafkaAdminClient)

    def _create_kafka_client(self, clazz):
        kafka_connect_str = self.instance.get('kafka_connect_str')
        if not isinstance(kafka_connect_str, (string_types, list)):
            raise ConfigurationError('kafka_connect_str should be string or list of strings')
        kafka_version = self.instance.get('kafka_client_api_version')
        if isinstance(kafka_version, str):
            kafka_version = tuple(map(int, kafka_version.split(".")))

        tls_context = self.get_tls_context()
        crlfile = self.instance.get('ssl_crlfile', self.instance.get('tls_crlfile'))
        if crlfile:
            tls_context.load_verify_locations(crlfile)
            tls_context.verify_flags |= ssl.VERIFY_CRL_CHECK_LEAF

        return clazz(
            bootstrap_servers=kafka_connect_str,
            client_id='dd-agent',
            request_timeout_ms=self.init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT) * 1000,
            # if `kafka_client_api_version` is not set, then kafka-python automatically probes the cluster for
            # broker version during the bootstrapping process. Note that this returns the first version found, so in
            # a mixed-version cluster this will be a non-deterministic result.
            api_version=kafka_version,
            # While we check for SASL/SSL params, if not present they will default to the kafka-python values for
            # plaintext connections
            security_protocol=self.instance.get('security_protocol', 'PLAINTEXT'),
            sasl_mechanism=self.instance.get('sasl_mechanism'),
            sasl_plain_username=self.instance.get('sasl_plain_username'),
            sasl_plain_password=self.instance.get('sasl_plain_password'),
            sasl_kerberos_service_name=self.instance.get('sasl_kerberos_service_name', 'kafka'),
            sasl_kerberos_domain_name=self.instance.get('sasl_kerberos_domain_name'),
            sasl_oauth_token_provider=(
                OAuthTokenProvider(**self.instance['sasl_oauth_token_provider'])
                if 'sasl_oauth_token_provider' in self.instance
                else None
            ),
            ssl_context=tls_context,
        )

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

    def check(self, _):
        """The main entrypoint of the check."""
        self._consumer_offsets = {}  # Expected format: {(consumer_group, topic, partition): offset}
        self._highwater_offsets = {}  # Expected format: {(topic, partition): offset}
        self.client = make_client(self)

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

    # TODO: Remove me once the tests are refactored
    def send_event(self, title, text, tags, event_type, aggregation_key, severity='info'):
        if self.client is None:
            self.client = make_client(self)
        self.client._send_event(title, text, tags, event_type, aggregation_key, severity='info')
