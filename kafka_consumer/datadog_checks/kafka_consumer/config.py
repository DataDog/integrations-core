# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.kafka_consumer.constants import CONTEXT_UPPER_BOUND, DEFAULT_KAFKA_TIMEOUT


class KafkaConfig:
    def __init__(self, init_config, instance, log) -> None:
        self.instance = instance
        self.init_config = init_config
        self._context_limit = int(init_config.get('max_partition_contexts', CONTEXT_UPPER_BOUND))
        self.log = log
        self._custom_tags = instance.get('tags', [])
        self._monitor_unlisted_consumer_groups = is_affirmative(instance.get('monitor_unlisted_consumer_groups', False))
        self._monitor_all_broker_highwatermarks = is_affirmative(
            instance.get('monitor_all_broker_highwatermarks', False)
        )
        self._consumer_groups = instance.get('consumer_groups', {})
        self._consumer_groups_regex = instance.get('consumer_groups_regex', {})

        self._consumer_groups_compiled_regex = (
            self._compile_regex(self._consumer_groups_regex, self._consumer_groups)
            if self._consumer_groups_regex
            else ""
        )

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

        if not isinstance(self._kafka_connect_str, (str, list)):
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

        # If `monitor_unlisted_consumer_groups` is set to true and
        # using `consumer_groups`, we prioritize `monitor_unlisted_consumer_groups`
        if self._monitor_unlisted_consumer_groups and (self._consumer_groups or self._consumer_groups_regex):
            self.log.warning(
                "Using both monitor_unlisted_consumer_groups and consumer_groups or consumer_groups_regex, "
                "so all consumer groups will be collected."
            )

        if self._consumer_groups and self._consumer_groups_regex:
            self.log.warning("Using consumer_groups and consumer_groups_regex, will combine the two config options.")

        if not (self._monitor_unlisted_consumer_groups or self._consumer_groups or self._consumer_groups_regex):
            raise ConfigurationError(
                "Cannot fetch consumer offsets because no consumer_groups are specified and "
                "monitor_unlisted_consumer_groups is %s." % self._monitor_unlisted_consumer_groups
            )

        self._validate_consumer_groups()

    def _compile_regex(self, consumer_groups_regex, consumer_groups):
        # Turn the dict of regex dicts into a single string and compile
        # (<CONSUMER_REGEX>,(TOPIC_REGEX),(PARTITION_REGEX))|(...)
        patterns = ""
        patterns += self.make_pattern(consumer_groups)
        patterns += self.make_pattern(consumer_groups_regex)

        # Remove last "|"
        patterns = patterns.rstrip(patterns[-1])
        final_pattern = re.compile(patterns)
        return final_pattern

    def make_pattern(self, consumer_groups):
        template = "({0},{1},{2})|"
        patterns = ""
        for consumer_group in consumer_groups:
            topics = consumer_groups.get(consumer_group)

            if not topics:
                patterns += template.format(consumer_group, ".+", ".+")
            else:
                for topic in topics:
                    partitions = consumer_groups[consumer_group][topic]
                    if not partitions:
                        patterns += template.format(consumer_group, topic, ".+")
                    else:
                        for partition in partitions:
                            patterns += template.format(consumer_group, topic, partition)
        return patterns

    def _validate_consumer_groups(self):
        """Validate any explicitly specified consumer groups.
        consumer_groups = {'consumer_group': {'topic': [0, 1]}}
        """
        if not isinstance(self._consumer_groups, dict):
            raise ConfigurationError("consumer_groups is not a dictionary")
        for consumer_group, topics in self._consumer_groups.items():
            if not isinstance(consumer_group, str):
                raise ConfigurationError("consumer group is not a valid string")
            if not (isinstance(topics, dict) or topics is None):  # topics are optional
                raise ConfigurationError("Topics is not a dictionary")
            if topics is not None:
                for topic, partitions in topics.items():
                    if not isinstance(topic, str):
                        raise ConfigurationError("Topic is not a valid string")
                    if not (isinstance(partitions, (list, tuple)) or partitions is None):  # partitions are optional
                        raise ConfigurationError("Partitions is not a list or tuple")
                    if partitions is not None:
                        for partition in partitions:
                            if not isinstance(partition, int):
                                raise ConfigurationError("Partition is not a valid integer")
