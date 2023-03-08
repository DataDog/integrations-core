# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import string_types

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.kafka_consumer.constants import (
    BROKER_REQUESTS_BATCH_SIZE,
    CONTEXT_UPPER_BOUND,
    DEFAULT_KAFKA_TIMEOUT,
)


class KafkaConfig:
    def __init__(self, init_config, instance) -> None:
        self.instance = instance
        self.init_config = init_config
        self._context_limit = int(init_config.get('max_partition_contexts', CONTEXT_UPPER_BOUND))
        self._custom_tags = instance.get('tags', [])
        self._monitor_unlisted_consumer_groups = is_affirmative(instance.get('monitor_unlisted_consumer_groups', False))
        self._monitor_all_broker_highwatermarks = is_affirmative(
            instance.get('monitor_all_broker_highwatermarks', False)
        )
        self._consumer_groups = instance.get('consumer_groups', {})
        self._broker_requests_batch_size = instance.get('broker_requests_batch_size', BROKER_REQUESTS_BATCH_SIZE)

        self._kafka_connect_str = instance.get('kafka_connect_str')

        self._kafka_version = instance.get('kafka_client_api_version')
        if isinstance(self._kafka_version, str):
            self._kafka_version = tuple(map(int, self._kafka_version.split(".")))
        self._crlfile = instance.get('ssl_crlfile', instance.get('tls_crlfile'))
        self._request_timeout_ms = init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT) * 1000
        self._security_protocol = instance.get('security_protocol', 'PLAINTEXT')
        self._sasl_mechanism = instance.get('sasl_mechanism')
        self._sasl_plain_username = instance.get('sasl_plain_username')
        self._sasl_plain_password = instance.get('sasl_plain_password')
        self._sasl_kerberos_service_name = instance.get('sasl_kerberos_service_name', 'kafka')
        self._sasl_kerberos_domain_name = instance.get('sasl_kerberos_domain_name')
        self._sasl_oauth_token_provider = instance.get('sasl_oauth_token_provider')
        self._sasl_kerberos_keytab = instance.get('sasl_kerberos_keytab')
        self.use_legacy_client = is_affirmative(instance.get('use_legacy_client', False))

    def validate_config(self):
        if not self._kafka_connect_str:
            raise ConfigurationError('`kafka_connect_str` is required')

        if not isinstance(self._kafka_connect_str, (string_types, list)):
            raise ConfigurationError('`kafka_connect_str` should be string or list of strings')

        if isinstance(self._kafka_connect_str, list):
            self._kafka_connect_str = ",".join(str(connect_str) for connect_str in self._kafka_connect_str)

        if isinstance(self._kafka_version, str):
            self._kafka_version = tuple(map(int, self._kafka_version.split(".")))

        if self._sasl_mechanism == "OAUTHBEARER":
            if self._sasl_oauth_token_provider is None:
                raise ConfigurationError("sasl_oauth_token_provider required for OAUTHBEARER sasl")

            if self._sasl_oauth_token_provider.get("url") is None:
                raise ConfigurationError("The `url` setting of `auth_token` reader is required")

            elif self._sasl_oauth_token_provider.get("client_id") is None:
                raise ConfigurationError("The `client_id` setting of `auth_token` reader is required")

            elif self._sasl_oauth_token_provider.get("client_secret") is None:
                raise ConfigurationError("The `client_secret` setting of `auth_token` reader is required")
