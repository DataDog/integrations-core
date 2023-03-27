# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from six import string_types

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.kafka_consumer.constants import CONTEXT_UPPER_BOUND, DEFAULT_KAFKA_TIMEOUT


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

        self._kafka_connect_str = instance.get('kafka_connect_str')

        self._kafka_version = instance.get('kafka_client_api_version')
        if isinstance(self._kafka_version, str):
            self._kafka_version = tuple(map(int, self._kafka_version.split(".")))
        self._crlfile = instance.get('ssl_crlfile', instance.get('tls_crlfile'))
        self._request_timeout = init_config.get('kafka_timeout', DEFAULT_KAFKA_TIMEOUT)
        self._request_timeout_ms = self._request_timeout * 1000
        self._security_protocol = instance.get('security_protocol', 'PLAINTEXT')
        self._sasl_mechanism = instance.get('sasl_mechanism')
        self._sasl_plain_username = instance.get('sasl_plain_username')
        self._sasl_plain_password = instance.get('sasl_plain_password')
        self._sasl_kerberos_service_name = instance.get('sasl_kerberos_service_name', 'kafka')
        self._sasl_kerberos_domain_name = instance.get('sasl_kerberos_domain_name')
        self._sasl_kerberos_keytab = instance.get('sasl_kerberos_keytab', os.environ.get("KRB5_CLIENT_KTNAME"))
        self._sasl_kerberos_principal = instance.get('sasl_kerberos_principal', 'kafkaclient')
        self._sasl_oauth_token_provider = instance.get('sasl_oauth_token_provider')
        self._tls_ca_cert = instance.get("tls_ca_cert")
        self._tls_cert = instance.get("tls_cert")
        self._tls_private_key = instance.get("tls_private_key")
        self._tls_private_key_password = instance.get("tls_private_key_password")
        self._tls_validate_hostname = is_affirmative(instance.get("tls_validate_hostname", True))

        if self._tls_cert or self._tls_ca_cert or self._tls_private_key or self._tls_private_key_password:
            self._tls_verify = True
        else:
            self._tls_verify = is_affirmative(instance.get("tls_verify", True))

    def validate_config(self):
        if not self._kafka_connect_str:
            raise ConfigurationError('`kafka_connect_str` is required')

        if not isinstance(self._kafka_connect_str, (string_types, list)):
            raise ConfigurationError('`kafka_connect_str` should be string or list of strings')

        if isinstance(self._kafka_connect_str, list):
            self._kafka_connect_str = ",".join(str(connect_str) for connect_str in self._kafka_connect_str)

        if isinstance(self._kafka_version, str):
            self._kafka_version = tuple(map(int, self._kafka_version.split(".")))
