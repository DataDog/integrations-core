# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import re

from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.sqlserver.const import DEFAULT_AUTODISCOVERY_INTERVAL, PROC_CHAR_LIMIT


class SQLServerConfig:
    def __init__(self, init_config, instance, log):
        self.log = log
        self.tags: list[str] = instance.get("tags", [])
        self.reported_hostname: str = instance.get('reported_hostname')
        self.autodiscovery: bool = is_affirmative(instance.get('database_autodiscovery'))
        self.autodiscovery_include: list[str] = instance.get('autodiscovery_include', ['.*']) or ['.*']
        self.autodiscovery_exclude: list[str] = instance.get('autodiscovery_exclude', ['model']) or ['model']
        self.autodiscovery_db_service_check: bool = is_affirmative(instance.get('autodiscovery_db_service_check', True))
        self.min_collection_interval: int = instance.get('min_collection_interval', 15)
        self.autodiscovery_interval: int = instance.get('autodiscovery_interval', DEFAULT_AUTODISCOVERY_INTERVAL)
        self._include_patterns = self._compile_valid_patterns(self.autodiscovery_include)
        self._exclude_patterns = self._compile_valid_patterns(self.autodiscovery_exclude)

        self.proc: str = instance.get('stored_procedure')
        self.custom_metrics: list[dict] = init_config.get('custom_metrics', []) or []
        self.include_index_usage_metrics_tempdb: bool = is_affirmative(
            instance.get('include_index_usage_metrics_tempdb', False)
        )
        self.include_db_fragmentation_metrics_tempdb: bool = is_affirmative(
            instance.get('include_db_fragmentation_metrics_tempdb', False)
        )
        self.ignore_missing_database = is_affirmative(instance.get("ignore_missing_database", False))
        if self.ignore_missing_database:
            self.log.warning(
                "The parameter 'ignore_missing_database' is deprecated"
                "if you are unsure about the database name please use 'database_autodiscovery'"
            )

        # DBM
        self.dbm_enabled: bool = is_affirmative(instance.get('dbm', False))
        self.statement_metrics_config: dict = instance.get('query_metrics', {}) or {}
        self.procedure_metrics_config: dict = instance.get('procedure_metrics', {}) or {}
        self.settings_config: dict = instance.get('collect_settings', {}) or {}
        self.activity_config: dict = instance.get('query_activity', {}) or {}
        self.cloud_metadata: dict = {}
        aws: dict = instance.get('aws', {}) or {}
        gcp: dict = instance.get('gcp', {}) or {}
        azure: dict = instance.get('azure', {}) or {}
        # Remap fully_qualified_domain_name to name
        azure = {k if k != 'fully_qualified_domain_name' else 'name': v for k, v in azure.items()}
        if aws:
            self.cloud_metadata.update({'aws': aws})
        if gcp:
            self.cloud_metadata.update({'gcp': gcp})
        if azure:
            self.cloud_metadata.update({'azure': azure})

        obfuscator_options_config: dict = instance.get('obfuscator_options', {}) or {}
        self.obfuscator_options: str = to_native_string(
            json.dumps(
                {
                    # Valid values for this can be found at
                    # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/semantic_conventions/database.md#connection-level-attributes
                    'dbms': 'mssql',
                    'replace_digits': is_affirmative(
                        obfuscator_options_config.get(
                            'replace_digits',
                            obfuscator_options_config.get('quantize_sql_tables', False),
                        )
                    ),
                    'keep_sql_alias': is_affirmative(obfuscator_options_config.get('keep_sql_alias', True)),
                    'return_json_metadata': is_affirmative(obfuscator_options_config.get('collect_metadata', True)),
                    'table_names': is_affirmative(obfuscator_options_config.get('collect_tables', True)),
                    'collect_commands': is_affirmative(obfuscator_options_config.get('collect_commands', True)),
                    'collect_comments': is_affirmative(obfuscator_options_config.get('collect_comments', True)),
                    # Config to enable/disable obfuscation of sql statements with go-sqllexer pkg
                    # Valid values for this can be found at https://github.com/DataDog/datadog-agent/blob/main/pkg/obfuscate/obfuscate.go#L108
                    'obfuscation_mode': obfuscator_options_config.get('obfuscation_mode', 'obfuscate_and_normalize'),
                    'remove_space_between_parentheses': is_affirmative(
                        obfuscator_options_config.get('remove_space_between_parentheses', False)
                    ),
                    'keep_null': is_affirmative(obfuscator_options_config.get('keep_null', False)),
                    'keep_boolean': is_affirmative(obfuscator_options_config.get('keep_boolean', False)),
                    'keep_positional_parameter': is_affirmative(
                        obfuscator_options_config.get('keep_positional_parameter', False)
                    ),
                    'keep_trailing_semicolon': is_affirmative(
                        obfuscator_options_config.get('keep_trailing_semicolon', False)
                    ),
                    'keep_identifier_quotation': is_affirmative(
                        obfuscator_options_config.get('keep_identifier_quotation', False)
                    ),
                }
            )
        )
        self.log_unobfuscated_queries: bool = is_affirmative(instance.get('log_unobfuscated_queries', False))
        self.log_unobfuscated_plans: bool = is_affirmative(instance.get('log_unobfuscated_plans', False))
        self.database_instance_collection_interval: int = instance.get('database_instance_collection_interval', 1800)
        self.stored_procedure_characters_limit: int = instance.get('stored_procedure_characters_limit', PROC_CHAR_LIMIT)
        self.connection_host: str = instance['host']

    def _compile_valid_patterns(self, patterns: list[str]) -> re.Pattern:
        valid_patterns = []

        for pattern in patterns:
            # Ignore empty patterns as they match everything
            if not pattern:
                continue

            try:
                re.compile(pattern, re.IGNORECASE)
            except Exception:
                self.log.warning('%s is not a valid regular expression and will be ignored', pattern)
            else:
                valid_patterns.append(pattern)

        if valid_patterns:
            return re.compile('|'.join(valid_patterns), re.IGNORECASE)
        else:
            # create unmatchable regex - https://stackoverflow.com/a/1845097/2157429
            return re.compile(r'(?!x)x')
