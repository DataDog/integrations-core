# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import ssl
from time import time

from kafka import KafkaAdminClient, KafkaClient
from kafka.oauth.abstract import AbstractTokenProvider
from six import string_types

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.http import AuthTokenOAuthReader

from .constants import CONTEXT_UPPER_BOUND, DEFAULT_KAFKA_TIMEOUT
from .new_kafka_consumer import NewKafkaConsumerCheck


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
        self.sub_check = None
        self._context_limit = int(self.init_config.get('max_partition_contexts', CONTEXT_UPPER_BOUND))
        self._data_streams_enabled = is_affirmative(self.instance.get('data_streams_enabled', False))
        self._custom_tags = self.instance.get('tags', [])
        self._monitor_unlisted_consumer_groups = is_affirmative(
            self.instance.get('monitor_unlisted_consumer_groups', False)
        )
        self._monitor_all_broker_highwatermarks = is_affirmative(
            self.instance.get('monitor_all_broker_highwatermarks', False)
        )
        self._consumer_groups = self.instance.get('consumer_groups', {})

        self.check_initializations.append(self._init_check_based_on_kafka_version)

    def check(self, _):
        return self.sub_check.check()

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

    def create_kafka_client(self):
        return self._create_kafka_client(clazz=KafkaClient)

    def create_kafka_admin_client(self):
        return self._create_kafka_client(clazz=KafkaAdminClient)

    def validate_consumer_groups(self):
        """Validate any explicitly specified consumer groups.

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

    def _init_check_based_on_kafka_version(self):
        """Set the sub_check attribute before allowing the `check` method to run. If something fails, this method will
        be retried regularly."""
        self.sub_check = NewKafkaConsumerCheck(self)

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
