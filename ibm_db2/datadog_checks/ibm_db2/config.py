# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.serialization import json


class IbmDb2Config:
    """Parse IBM Db2 instance and DBM options."""

    def __init__(self, init_config: dict, instance: dict, log) -> None:
        self.log = log
        self.db: str = instance.get('db', '')
        self.username: str = instance.get('username', '')
        self.password: str = instance.get('password', '')
        self.host: str = instance.get('host', '')
        self.port: int = instance.get('port', 50000)
        self.tags: list[str] = list(instance.get('tags', []) or [])
        self.security: str = instance.get('security', 'none')
        self.tls_cert: str | None = instance.get('tls_cert')
        self.connection_timeout: int | None = instance.get('connection_timeout')
        self.service: str = instance.get('service') or init_config.get('service') or ''
        self.min_collection_interval: float = instance.get('min_collection_interval', 15)
        self.collect_container_metrics: bool = is_affirmative(instance.get('collect_container_metrics', False))

        self.dbm_enabled: bool = is_affirmative(instance.get('dbm', False))
        self.database_identifier: dict = instance.get('database_identifier', {}) or {}
        self.database_instance_collection_interval: float = instance.get('database_instance_collection_interval', 300)
        self.collect_wlm_service_class_metrics: bool = is_affirmative(
            instance.get('collect_wlm_service_class_metrics', False)
        )
        self.reported_hostname: str | None = instance.get('reported_hostname')
        self.exclude_hostname: bool = is_affirmative(instance.get('exclude_hostname', False))
        self.query_metrics_config: dict = instance.get('query_metrics', {}) or {}
        self.query_samples_config: dict = instance.get('query_samples', {}) or {}
        self.activity_config: dict = instance.get('query_activity', {}) or {}
        self.settings_config: dict = instance.get('collect_settings', {}) or {}
        self.schemas_config: dict = instance.get('collect_schemas', {}) or {}
        self.collect_raw_query_statement: dict = instance.get('collect_raw_query_statement', {}) or {}
        self.log_unobfuscated_queries: bool = is_affirmative(instance.get('log_unobfuscated_queries', False))
        self.cloud_metadata: dict = self._build_cloud_metadata(instance)
        self.obfuscator_options: str = self._build_obfuscator_options(instance)

    def _build_cloud_metadata(self, instance: dict) -> dict:
        cloud_metadata = {}
        for cloud_provider in ('aws', 'gcp', 'azure'):
            metadata = instance.get(cloud_provider, {}) or {}
            if metadata:
                cloud_metadata[cloud_provider] = metadata
        return cloud_metadata

    def _build_obfuscator_options(self, instance: dict) -> str:
        obfuscator_options = instance.get('obfuscator_options', {}) or {}
        return to_native_string(
            json.dumps(
                {
                    'dbms': obfuscator_options.get('dbms', 'db2'),
                    'replace_digits': is_affirmative(obfuscator_options.get('replace_digits', False)),
                    'keep_sql_alias': is_affirmative(obfuscator_options.get('keep_sql_alias', True)),
                    'return_json_metadata': is_affirmative(obfuscator_options.get('collect_metadata', True)),
                    'table_names': is_affirmative(obfuscator_options.get('collect_tables', True)),
                    'collect_commands': is_affirmative(obfuscator_options.get('collect_commands', True)),
                    'collect_comments': is_affirmative(obfuscator_options.get('collect_comments', True)),
                    'collect_procedures': is_affirmative(obfuscator_options.get('collect_procedures', True)),
                    'obfuscation_mode': obfuscator_options.get('obfuscation_mode', 'obfuscate_and_normalize'),
                    'remove_space_between_parentheses': is_affirmative(
                        obfuscator_options.get('remove_space_between_parentheses', False)
                    ),
                    'keep_null': is_affirmative(obfuscator_options.get('keep_null', False)),
                    'keep_boolean': is_affirmative(obfuscator_options.get('keep_boolean', False)),
                    'keep_positional_parameter': is_affirmative(
                        obfuscator_options.get('keep_positional_parameter', False)
                    ),
                    'replace_bind_parameter': is_affirmative(obfuscator_options.get('replace_bind_parameter', False)),
                    'keep_trailing_semicolon': is_affirmative(obfuscator_options.get('keep_trailing_semicolon', False)),
                    'keep_identifier_quotation': is_affirmative(
                        obfuscator_options.get('keep_identifier_quotation', False)
                    ),
                }
            )
        )
