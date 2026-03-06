# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import ConfigurationError, is_affirmative


class KafkaActionsConfig:
    """Configuration validator for Kafka Actions integration."""

    def __init__(self, instance, log):
        self.instance = instance
        self.log = log

        self.remote_config_id = instance.get('remote_config_id')
        self.kafka_connect_str = instance.get('kafka_connect_str')
        self.tags = instance.get('tags', [])

        # Authentication fields (same pattern as kafka_consumer)
        self._security_protocol = instance.get('security_protocol', 'PLAINTEXT')
        self._sasl_mechanism = instance.get('sasl_mechanism')
        self._sasl_plain_username = instance.get('sasl_plain_username')
        self._sasl_plain_password = instance.get('sasl_plain_password')
        self._sasl_kerberos_service_name = instance.get('sasl_kerberos_service_name', 'kafka')
        self._sasl_kerberos_domain_name = instance.get('sasl_kerberos_domain_name')
        self._sasl_kerberos_keytab = instance.get('sasl_kerberos_keytab', os.environ.get("KRB5_CLIENT_KTNAME"))
        self._sasl_kerberos_principal = instance.get('sasl_kerberos_principal', 'kafkaclient')
        self._sasl_oauth_token_provider = instance.get('sasl_oauth_token_provider')

        self._tls_ca_cert = instance.get('tls_ca_cert')
        self._tls_cert = instance.get('tls_cert')
        self._tls_private_key = instance.get('tls_private_key')
        self._tls_private_key_password = instance.get('tls_private_key_password')
        self._tls_validate_hostname = is_affirmative(instance.get('tls_validate_hostname', True))
        self._crlfile = instance.get('tls_crlfile')

        if self._tls_cert or self._tls_ca_cert or self._tls_private_key or self._tls_private_key_password:
            self._tls_verify = "true"
        else:
            self._tls_verify = "true" if is_affirmative(instance.get("tls_verify", True)) else "false"

        if (
            not self._tls_ca_cert
            and os.name != 'nt'
            and os.path.exists('/opt/datadog-agent/embedded/ssl/certs/cacert.pem')
        ):
            self._tls_ca_cert = '/opt/datadog-agent/embedded/ssl/certs/cacert.pem'

        self._sasl_oauth_tls_ca_cert = (
            self._sasl_oauth_token_provider.get("tls_ca_cert") if self._sasl_oauth_token_provider else None
        )

        self.read_messages = instance.get('read_messages')
        self.create_topic = instance.get('create_topic')
        self.update_topic_config = instance.get('update_topic_config')
        self.delete_topic = instance.get('delete_topic')
        self.delete_consumer_group = instance.get('delete_consumer_group')
        self.update_consumer_group_offsets = instance.get('update_consumer_group_offsets')
        self.produce_message = instance.get('produce_message')

        self.action = self._detect_action()

    def _detect_action(self) -> str | None:
        """Auto-detect which action to execute based on config structure.

        Returns:
            Action name, or None if no action detected
        """
        action_handlers = [
            'read_messages',
            'create_topic',
            'update_topic_config',
            'delete_topic',
            'delete_consumer_group',
            'update_consumer_group_offsets',
            'produce_message',
        ]

        for action_name in action_handlers:
            if action_name in self.instance:
                return action_name

        return None

    def validate_config(self):
        """Validate the entire configuration."""
        if not self.remote_config_id:
            raise ConfigurationError(
                "remote_config_id is required. This integration must be configured via Remote Configuration."
            )

        if not self.kafka_connect_str:
            raise ConfigurationError("kafka_connect_str is required")

        self._validate_auth()

        if not self.action:
            raise ConfigurationError(
                "No action detected in configuration. "
                "Please include one of: read_messages, create_topic, update_topic_config, "
                "delete_topic, delete_consumer_group, update_consumer_group_offsets, produce_message"
            )

        if self.action == 'read_messages':
            self._validate_read_messages()
        elif self.action == 'create_topic':
            self._validate_create_topic()
        elif self.action == 'update_topic_config':
            self._validate_update_topic_config()
        elif self.action == 'delete_topic':
            self._validate_delete_topic()
        elif self.action == 'delete_consumer_group':
            self._validate_delete_consumer_group()
        elif self.action == 'update_consumer_group_offsets':
            self._validate_update_consumer_group_offsets()
        elif self.action == 'produce_message':
            self._validate_produce_message()

    def _validate_auth(self):
        """Validate authentication configuration."""
        if self._sasl_mechanism == 'OAUTHBEARER':
            if self._sasl_oauth_token_provider is None:
                raise ConfigurationError("sasl_oauth_token_provider required for OAUTHBEARER sasl")

            if not isinstance(self._sasl_oauth_token_provider, dict):
                raise ConfigurationError(
                    f"sasl_oauth_token_provider must be a dictionary. Got: {type(self._sasl_oauth_token_provider)}"
                )

            method = self._sasl_oauth_token_provider.get('method', 'oidc')

            if method == 'aws_msk_iam':
                aws_region = self._sasl_oauth_token_provider.get('aws_region')
                if not aws_region:
                    try:
                        import boto3

                        detected_region = boto3.session.Session().region_name
                        if not detected_region:
                            self.log.warning(
                                "AWS region cannot be detected automatically for MSK IAM authentication. "
                                "Consider specifying 'aws_region' in sasl_oauth_token_provider configuration."
                            )
                    except ImportError:
                        raise ConfigurationError(
                            "AWS MSK IAM authentication requires 'boto3' and 'aws-msk-iam-sasl-signer-python' "
                            "libraries. Install them with: pip install boto3 aws-msk-iam-sasl-signer-python"
                        )
            elif method == 'oidc':
                if self._sasl_oauth_token_provider.get('url') is None:
                    raise ConfigurationError("The `url` setting of `auth_token` reader is required")

                if self._sasl_oauth_token_provider.get('client_id') is None:
                    raise ConfigurationError("The `client_id` setting of `auth_token` reader is required")

                if self._sasl_oauth_token_provider.get('client_secret') is None:
                    raise ConfigurationError("The `client_secret` setting of `auth_token` reader is required")
            else:
                raise ConfigurationError(
                    f"Invalid method '{method}' for sasl_oauth_token_provider. Must be 'aws_msk_iam' or 'oidc'"
                )

    def _validate_read_messages(self):
        """Validate read_messages action configuration."""
        config = self.read_messages

        if not config.get('cluster'):
            raise ConfigurationError("read_messages action requires 'cluster' parameter")

        if not config.get('topic'):
            raise ConfigurationError("read_messages action requires 'topic' parameter")

        # Note: n_messages_retrieved and max_scanned_messages are validated in the Datadog backend

        value_format = config.get('value_format', 'json')
        if value_format not in ['json', 'bson', 'string', 'protobuf', 'avro']:
            raise ConfigurationError(
                f"Invalid value_format: {value_format}. Supported formats: json, bson, string, protobuf, avro"
            )

        key_format = config.get('key_format', 'json')
        if key_format not in ['json', 'bson', 'string', 'protobuf', 'avro']:
            raise ConfigurationError(
                f"Invalid key_format: {key_format}. Supported formats: json, bson, string, protobuf, avro"
            )

        schema_registry_url = self.instance.get('schema_registry_url')

        if value_format in ['protobuf', 'avro']:
            if config.get('value_uses_schema_registry'):
                if not schema_registry_url:
                    raise ConfigurationError(
                        f"value_format='{value_format}' with 'value_uses_schema_registry=true' "
                        f"requires 'schema_registry_url' to be configured"
                    )
            elif not config.get('value_schema'):
                raise ConfigurationError(
                    f"value_format='{value_format}' requires either 'value_uses_schema_registry=true' "
                    f"or 'value_schema' to be specified"
                )

        if key_format in ['protobuf', 'avro']:
            if config.get('key_uses_schema_registry'):
                if not schema_registry_url:
                    raise ConfigurationError(
                        f"key_format='{key_format}' with 'key_uses_schema_registry=true' "
                        f"requires 'schema_registry_url' to be configured"
                    )
            elif not config.get('key_schema'):
                raise ConfigurationError(
                    f"key_format='{key_format}' requires either 'key_uses_schema_registry=true' "
                    f"or 'key_schema' to be specified"
                )

    def _validate_create_topic(self):
        """Validate create_topic action configuration."""
        config = self.create_topic

        if not config.get('cluster'):
            raise ConfigurationError("create_topic action requires 'cluster' parameter")

        if not config.get('topic'):
            raise ConfigurationError("create_topic action requires 'topic' parameter")

        if 'num_partitions' not in config:
            raise ConfigurationError("create_topic action requires 'num_partitions' parameter")

        if 'replication_factor' not in config:
            raise ConfigurationError("create_topic action requires 'replication_factor' parameter")

        num_partitions = config.get('num_partitions')
        if not isinstance(num_partitions, int) or num_partitions < 1:
            raise ConfigurationError("num_partitions must be a positive integer")

        replication_factor = config.get('replication_factor')
        if not isinstance(replication_factor, int) or replication_factor < 1:
            raise ConfigurationError("replication_factor must be a positive integer")

    def _validate_update_topic_config(self):
        """Validate update_topic_config action configuration."""
        config = self.update_topic_config

        if not config.get('cluster'):
            raise ConfigurationError("update_topic_config action requires 'cluster' parameter")

        if not config.get('topic'):
            raise ConfigurationError("update_topic_config action requires 'topic' parameter")

        if not config.get('num_partitions') and not config.get('configs') and not config.get('delete_configs'):
            raise ConfigurationError(
                "update_topic_config action requires at least one of: 'num_partitions', 'configs', or 'delete_configs'"
            )

        num_partitions = config.get('num_partitions')
        if num_partitions is not None:
            if not isinstance(num_partitions, int) or num_partitions < 1:
                raise ConfigurationError("num_partitions must be a positive integer")

    def _validate_delete_topic(self):
        """Validate delete_topic action configuration."""
        config = self.delete_topic

        if not config.get('cluster'):
            raise ConfigurationError("delete_topic action requires 'cluster' parameter")

        if not config.get('topic'):
            raise ConfigurationError("delete_topic action requires 'topic' parameter")

    def _validate_delete_consumer_group(self):
        """Validate delete_consumer_group action configuration."""
        config = self.delete_consumer_group

        if not config.get('cluster'):
            raise ConfigurationError("delete_consumer_group action requires 'cluster' parameter")

        if not config.get('consumer_group'):
            raise ConfigurationError("delete_consumer_group action requires 'consumer_group' parameter")

    def _validate_update_consumer_group_offsets(self):
        """Validate update_consumer_group_offsets action configuration."""
        config = self.update_consumer_group_offsets

        if not config.get('cluster'):
            raise ConfigurationError("update_consumer_group_offsets action requires 'cluster' parameter")

        if not config.get('consumer_group'):
            raise ConfigurationError("update_consumer_group_offsets action requires 'consumer_group' parameter")

        offsets = config.get('offsets', [])
        if not offsets:
            raise ConfigurationError("update_consumer_group_offsets action requires 'offsets' list")

        for i, offset_entry in enumerate(offsets):
            if not isinstance(offset_entry, dict):
                raise ConfigurationError(f"offsets[{i}] must be a dictionary")

            if not offset_entry.get('topic'):
                raise ConfigurationError(f"offsets[{i}] requires 'topic' parameter")

            if 'partition' not in offset_entry:
                raise ConfigurationError(f"offsets[{i}] requires 'partition' parameter")

            if 'offset' not in offset_entry:
                raise ConfigurationError(f"offsets[{i}] requires 'offset' parameter")

            if not isinstance(offset_entry.get('partition'), int):
                raise ConfigurationError(f"offsets[{i}].partition must be an integer")

            if not isinstance(offset_entry.get('offset'), int):
                raise ConfigurationError(f"offsets[{i}].offset must be an integer")

    def _validate_produce_message(self):
        """Validate produce_message action configuration."""
        config = self.produce_message

        if not config.get('cluster'):
            raise ConfigurationError("produce_message action requires 'cluster' parameter")

        if not config.get('topic'):
            raise ConfigurationError("produce_message action requires 'topic' parameter")

        if not config.get('value'):
            raise ConfigurationError("produce_message action requires 'value' parameter")
