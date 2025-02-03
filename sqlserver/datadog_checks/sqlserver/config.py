# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import re

from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.utils import get_agent_host_tags
from datadog_checks.sqlserver.const import (
    DEFAULT_AUTODISCOVERY_INTERVAL,
    DEFAULT_LONG_METRICS_COLLECTION_INTERVAL,
    PROC_CHAR_LIMIT,
)


class SQLServerConfig:
    def __init__(self, init_config, instance, log):
        self.log = log
        self.reported_hostname: str = instance.get('reported_hostname')
        self.autodiscovery: bool = is_affirmative(instance.get('database_autodiscovery'))
        self.autodiscovery_include: list[str] = instance.get('autodiscovery_include', ['.*']) or ['.*']
        self.autodiscovery_exclude: list[str] = instance.get('autodiscovery_exclude', ['model']) or ['model']
        self.autodiscovery_db_service_check: bool = is_affirmative(instance.get('autodiscovery_db_service_check', True))
        self.min_collection_interval: int = instance.get('min_collection_interval', 15)
        self.autodiscovery_interval: int = instance.get('autodiscovery_interval', DEFAULT_AUTODISCOVERY_INTERVAL)
        self.database_instance_collection_interval: int = instance.get(
            'database_instance_collection_interval', DEFAULT_LONG_METRICS_COLLECTION_INTERVAL
        )
        self._include_patterns = self._compile_valid_patterns(self.autodiscovery_include)
        self._exclude_patterns = self._compile_valid_patterns(self.autodiscovery_exclude)

        self.proc: str = instance.get('stored_procedure')
        self.custom_metrics: list[dict] = init_config.get('custom_metrics', []) or []
        self.ignore_missing_database = is_affirmative(instance.get("ignore_missing_database", False))
        if self.ignore_missing_database:
            self.log.warning(
                "The parameter 'ignore_missing_database' is deprecated"
                "if you are unsure about the database name please use 'database_autodiscovery'"
            )

        # DBM
        self.dbm_enabled: bool = is_affirmative(instance.get('dbm', False))
        self.database_metrics_config: dict = self._build_database_metrics_configs(instance)
        self.statement_metrics_config: dict = instance.get('query_metrics', {}) or {}
        self.agent_jobs_config: dict = instance.get('agent_jobs', {}) or {}
        self.procedure_metrics_config: dict = instance.get('procedure_metrics', {}) or {}
        self.settings_config: dict = instance.get('collect_settings', {}) or {}
        self.activity_config: dict = instance.get('query_activity', {}) or {}
        self.schema_config: dict = instance.get('schemas_collection', {}) or {}
        self.deadlocks_config: dict = instance.get('deadlocks_collection', {}) or {}
        self.cloud_metadata: dict = {}
        aws: dict = instance.get('aws', {}) or {}
        gcp: dict = instance.get('gcp', {}) or {}
        azure: dict = instance.get('azure', {}) or {}
        if aws:
            self.cloud_metadata.update({'aws': aws})
        if gcp:
            self.cloud_metadata.update({'gcp': gcp})
        if azure:
            # Remap fully_qualified_domain_name to name
            if 'fully_qualified_domain_name' in azure:
                azure['name'] = azure.pop('fully_qualified_domain_name')
            azure['aggregate_sql_databases'] = is_affirmative(azure.get('aggregate_sql_databases', False))
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
        collect_raw_query_statement_config: dict = instance.get('collect_raw_query_statement', {}) or {}
        self.collect_raw_query_statement = {
            "enabled": is_affirmative(collect_raw_query_statement_config.get('enabled', False)),
            "cache_max_size": int(collect_raw_query_statement_config.get('cache_max_size', 10000)),
            "samples_per_hour_per_query": int(collect_raw_query_statement_config.get('samples_per_hour_per_query', 1)),
        }
        self.log_unobfuscated_queries: bool = is_affirmative(instance.get('log_unobfuscated_queries', False))
        self.log_unobfuscated_plans: bool = is_affirmative(instance.get('log_unobfuscated_plans', False))
        self.stored_procedure_characters_limit: int = instance.get('stored_procedure_characters_limit', PROC_CHAR_LIMIT)
        self.connection_host: str = instance['host']
        self.service = instance.get('service') or init_config.get('service') or ''
        self.db_fragmentation_object_names = instance.get('db_fragmentation_object_names', []) or []

        self.tags: list[str] = self._build_tags(
            custom_tags=instance.get('tags', []),
            propagate_agent_tags=self._should_propagate_agent_tags(instance, init_config),
            additional_tags=["raw_query_statement:enabled"] if self.collect_raw_query_statement["enabled"] else [],
        )

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

    def _build_tags(self, custom_tags, propagate_agent_tags, additional_tags):
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if custom_tags is None:
            tags = []
        else:
            tags = list(set(custom_tags))

        if propagate_agent_tags:
            try:
                agent_tags = get_agent_host_tags()
                tags.extend(agent_tags)
            except Exception as e:
                raise ConfigurationError(
                    'propagate_agent_tags enabled but there was an error fetching agent tags {}'.format(e)
                )

        if additional_tags:
            tags.extend(additional_tags)
        return tags

    @staticmethod
    def _should_propagate_agent_tags(instance, init_config) -> bool:
        '''
        return True if the agent tags should be propagated to the check
        '''
        instance_propagate_agent_tags = instance.get('propagate_agent_tags')
        init_config_propagate_agent_tags = init_config.get('propagate_agent_tags')

        if instance_propagate_agent_tags is not None:
            # if the instance has explicitly set the value, return the boolean
            return instance_propagate_agent_tags
        if init_config_propagate_agent_tags is not None:
            # if the init_config has explicitly set the value, return the boolean
            return init_config_propagate_agent_tags
        # if neither the instance nor the init_config has set the value, return False
        return False

    def _build_database_metrics_configs(self, instance):
        # Set defaults for database metrics
        configurable_metrics = {
            "ao_metrics": {'enabled': False, 'availability_group': None, 'ao_database': None, 'only_emit_local': False},
            "db_backup_metrics": {'enabled': True, 'collection_interval': DEFAULT_LONG_METRICS_COLLECTION_INTERVAL},
            "db_files_metrics": {'enabled': True},
            "db_stats_metrics": {'enabled': True},
            "db_fragmentation_metrics": {
                'enabled': False,
                'enabled_tempdb': False,
                'collection_interval': DEFAULT_LONG_METRICS_COLLECTION_INTERVAL,
            },
            "fci_metrics": {'enabled': False},
            "file_stats_metrics": {'enabled': True},
            "index_usage_metrics": {
                'enabled': True,
                'collection_interval': DEFAULT_LONG_METRICS_COLLECTION_INTERVAL,
                'enabled_tempdb': False,
            },
            "instance_metrics": {'enabled': True},
            "master_files_metrics": {'enabled': False},
            "primary_log_shipping_metrics": {'enabled': False},
            "secondary_log_shipping_metrics": {'enabled': False},
            "server_state_metrics": {'enabled': True},
            "task_scheduler_metrics": {'enabled': False},
            "tempdb_file_space_usage_metrics": {'enabled': True},
            "xe_metrics": {'enabled': False},
        }
        # Check if the instance has any configuration for the metrics in legacy structure
        legacy_configuration_metrics = {
            "include_ao_metrics": "ao_metrics",
            "include_master_files_metrics": "master_files_metrics",
            "include_fci_metrics": "fci_metrics",
            "include_primary_log_shipping_metrics": "primary_log_shipping_metrics",
            "include_secondary_log_shipping_metrics": "secondary_log_shipping_metrics",
            "include_instance_metrics": "instance_metrics",
            "include_task_scheduler_metrics": "task_scheduler_metrics",
            "include_db_fragmentation_metrics": "db_fragmentation_metrics",
            "include_index_usage_metrics": "index_usage_metrics",
            "include_tempdb_file_space_usage_metrics": "tempdb_file_space_usage_metrics",
            "include_xe_metrics": "xe_metrics",
        }
        for metric, config_key in legacy_configuration_metrics.items():
            if instance.get(metric) is not None:
                configurable_metrics[config_key]['enabled'] = instance[metric]
        # Manual look ups for legacy configuration structure
        configurable_metrics['ao_metrics']['availability_group'] = instance.get(
            'availability_group', configurable_metrics['ao_metrics']['availability_group']
        )
        configurable_metrics['ao_metrics']['ao_database'] = instance.get(
            'ao_database', configurable_metrics['ao_metrics']['ao_database']
        )
        configurable_metrics['ao_metrics']['only_emit_local'] = instance.get(
            'only_emit_local', configurable_metrics['ao_metrics']['only_emit_local']
        )
        configurable_metrics['db_backup_metrics']['collection_interval'] = instance.get(
            'database_backup_metrics_interval', configurable_metrics['db_backup_metrics']['collection_interval']
        )
        configurable_metrics['db_fragmentation_metrics']['enabled_tempdb'] = instance.get(
            'include_db_fragmentation_metrics_tempdb',
            configurable_metrics['db_fragmentation_metrics']['enabled_tempdb'],
        )
        configurable_metrics['db_fragmentation_metrics']['collection_interval'] = instance.get(
            'db_fragmentation_metrics_interval', configurable_metrics['db_fragmentation_metrics']['collection_interval']
        )
        configurable_metrics['index_usage_metrics']['enabled_tempdb'] = instance.get(
            'include_index_usage_metrics_tempdb', configurable_metrics['index_usage_metrics']['enabled_tempdb']
        )
        configurable_metrics['index_usage_metrics']['collection_interval'] = instance.get(
            'index_usage_stats_interval', configurable_metrics['index_usage_metrics']['collection_interval']
        )
        # Check if the instance has any configuration for the metrics
        database_metrics = instance.get('database_metrics', {})
        for metric, config in configurable_metrics.items():
            metric_config = database_metrics.get(metric, {})
            for key, value in metric_config.items():
                if value is not None:
                    config[key] = value
        return configurable_metrics
