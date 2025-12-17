# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
The goal of these tests are to verify our default configuration values are correct and remain consistent.
Failing tests indicate a regression in our defaults and should be looked inspected carefully.
Default values are duplicated within this file by design to ensure tests fail if the value changes unexpectedly.
"""

from unittest.mock import MagicMock

import pytest

from datadog_checks.postgres.config import build_config


# Single source of truth for all expected default values
# Organized by category for readability
EXPECTED_DEFAULTS = {
    # === Required fields (no defaults) ===
    'host': None,  # Required, user must provide
    'username': None,  # Required, user must provide
    'password': None,  # Required, user must provide (optional for managed auth)

    # === Connection configuration ===
    'port': 5432,
    'dbname': 'postgres',
    'ssl': 'allow',
    'ssl_root_cert': None,
    'ssl_cert': None,
    'ssl_key': None,
    'ssl_password': None,
    'query_timeout': 5000,
    'idle_connection_timeout': 60000,
    'max_connections': 30,
    'application_name': 'datadog-agent',

    # === Identification ===
    'reported_hostname': None,
    'exclude_hostname': False,
    'data_directory': '/usr/local/pgsql/data',
    'database_identifier': {
        'template': '$resolved_hostname',
    },

    # === Metric collection toggles ===
    'dbstrict': False,
    'collect_function_metrics': False,
    'collect_count_metrics': True,
    'collect_checksum_metrics': False,
    'collect_activity_metrics': False,
    'collect_buffercache_metrics': False,
    'collect_database_size_metrics': True,
    'collect_default_database': True,
    'collect_bloat_metrics': False,
    'collect_wal_metrics': True,
    'tag_replication_role': True,
    'table_count_limit': 200,
    'max_relations': 300,

    # === Database filtering ===
    'ignore_databases': [
        'template0',
        'template1',
        'rdsadmin',
        'azure_maintenance',
        'cloudsqladmin',
        'alloydbadmin',
        'alloydbmetadata',
    ],
    'ignore_schemas_owned_by': [
        'rds_superuser',
        'rdsadmin',
    ],

    # === Database monitoring (DBM) ===
    'dbm': False,
    'pg_stat_statements_view': 'pg_stat_statements',
    'pg_stat_activity_view': 'pg_stat_activity',
    'log_unobfuscated_queries': False,
    'log_unobfuscated_plans': False,
    'database_instance_collection_interval': 300,

    # === DBM: Query metrics ===
    'query_metrics': {
        'enabled': True,
        'collection_interval': 10,
        'pg_stat_statements_max_warning_threshold': 10000,
        'incremental_query_metrics': False,
        'baseline_metrics_expiry': 300,
        'full_statement_text_cache_max_size': 10000,
        'full_statement_text_samples_per_hour_per_query': 1,
        'run_sync': False,
    },

    # === DBM: Query samples ===
    'query_samples': {
        'enabled': True,
        'collection_interval': 1,
        'explain_function': 'datadog.explain_statement',
        'explained_queries_per_hour_per_query': 60,
        'samples_per_hour_per_query': 15,
        'explained_queries_cache_maxsize': 5000,
        'seen_samples_cache_maxsize': 10000,
        'explain_parameterized_queries': True,
        'explain_errors_cache_maxsize': 5000,
        'explain_errors_cache_ttl': 86400,
        'run_sync': False,
    },

    # === DBM: Query activity ===
    'query_activity': {
        'enabled': True,
        'collection_interval': 10,
        'payload_row_limit': 3500,
    },

    # === DBM: Settings collection ===
    'collect_settings': {
        'enabled': True,
        'collection_interval': 600,
        'run_sync': False,
        'ignored_settings_patterns': ['plpgsql%'],
    },

    # === DBM: Schema collection ===
    'collect_schemas': {
        'enabled': False,
        'max_tables': 300,
        'max_columns': 50,
        'collection_interval': 600,
        'max_query_duration': 60,
    },

    # === DBM: Obfuscator options ===
    'obfuscator_options': {
        'obfuscation_mode': 'obfuscate_and_normalize',
        'replace_digits': False,
        'collect_metadata': True,
        'collect_tables': True,
        'collect_commands': True,
        'collect_comments': True,
        'keep_sql_alias': True,
        'keep_dollar_quoted_func': True,
        'remove_space_between_parentheses': False,
        'keep_null': False,
        'keep_boolean': False,
        'keep_positional_parameter': False,
        'keep_trailing_semicolon': False,
        'keep_identifier_quotation': False,
        'keep_json_path': False,
    },

    # === DBM: Database autodiscovery ===
    'database_autodiscovery': {
        'enabled': False,
        'global_view_db': 'postgres',
        'max_databases': 100,
        'refresh': 600,
        'exclude': ['cloudsqladmin', 'rdsadmin', 'alloydbadmin', 'alloydbmetadata'],
        'include': ['.*'],
    },

    # === DBM: Lock metrics ===
    'locks_idle_in_transaction': {
        'enabled': True,
        'collection_interval': 300,
        'max_rows': 100,
    },

    # === DBM: Raw query statements ===
    'collect_raw_query_statement': {
        'enabled': False,
    },

    # === Relations configuration ===
    'relations': [],

    # === Query encodings ===
    'query_encodings': ['utf8'],

    # === Activity metrics ===
    'activity_metrics_excluded_aggregations': [],

    # === Cloud provider configurations ===
    'aws': {
        'instance_endpoint': None,
        'region': None,
        'managed_authentication': {'enabled': None},
    },
    'azure': {
        'deployment_type': None,
        'fully_qualified_domain_name': None,
        'managed_authentication': {'enabled': None},
    },
    'gcp': {
        'project_id': None,
        'instance_id': None,
    },

    # === Tagging ===
    'tags': ('server:localhost', 'port:5432', 'db:postgres'),  # Dynamically generated from connection info
    'disable_generic_tags': False,
    'propagate_agent_tags': False,

    # === Custom metrics/queries (deprecated/user-provided) ===
    'custom_metrics': (),  # Deprecated field, defaults to empty tuple
    'custom_queries': (),  # User-provided queries, defaults to empty tuple
    'only_custom_queries': False,  # Flag to run only custom queries
    'use_global_custom_queries': 'true',  # Use custom queries from init_config
    'service': None,  # User-provided service name
    'metric_patterns': None,  # User-provided patterns

    # === Agent standard fields ===
    'min_collection_interval': 15.0,  # Standard Agent field
    'empty_default_hostname': False,  # Deprecated field
}


@pytest.fixture
def mock_check():
    """Mock check object with a warning method."""
    check = MagicMock()
    check.warning = MagicMock()
    return check


@pytest.fixture
def minimal_instance():
    """Minimal instance configuration with only required fields."""
    return {
        'host': 'localhost',
        'username': 'testuser',
        'password': 'testpass',
    }


pytestmark = pytest.mark.unit


def test_all_config_defaults(mock_check, minimal_instance):
    """
    Verify that all InstanceConfig fields have the expected default values.

    This test iterates through every field in InstanceConfig and validates its default.
    If a field is missing from EXPECTED_DEFAULTS, the test will fail with instructions.
    """
    from datadog_checks.postgres.config_models.instance import InstanceConfig

    # Build config with minimal instance
    mock_check.instance = minimal_instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)

    # Get all fields from InstanceConfig
    all_fields = set(InstanceConfig.__annotations__.keys())

    # Check for fields in InstanceConfig that aren't in EXPECTED_DEFAULTS
    missing_from_expected = all_fields - set(EXPECTED_DEFAULTS.keys())
    if missing_from_expected:
        error_msg = (
            f"\n\n{'=' * 80}\n"
            f"MISSING EXPECTED DEFAULTS!\n"
            f"{'=' * 80}\n\n"
            f"The following fields exist in InstanceConfig but are missing from EXPECTED_DEFAULTS:\n"
            f"  {sorted(missing_from_expected)}\n\n"
            f"To fix this:\n"
            f"Add each field to the EXPECTED_DEFAULTS dictionary in test_config_defaults.py\n"
            f"with its expected default value.\n\n"
            f"Examples:\n"
            f"  - Simple field: 'field_name': default_value,\n"
            f"  - No default (user-provided): 'field_name': None,\n"
            f"  - Nested object: 'field_name': {{'key': 'value'}},\n"
            f"  - Array: 'field_name': ['item1', 'item2'],\n\n"
            f"{'=' * 80}\n"
        )
        pytest.fail(error_msg)

    # Check for fields in EXPECTED_DEFAULTS that aren't in InstanceConfig (cleanup needed)
    extra_in_expected = set(EXPECTED_DEFAULTS.keys()) - all_fields
    if extra_in_expected:
        pytest.fail(
            f"\n\nThe following fields are in EXPECTED_DEFAULTS but don't exist in InstanceConfig:\n"
            f"  {sorted(extra_in_expected)}\n"
            f"These should be removed from EXPECTED_DEFAULTS."
        )

    # Required fields that come from minimal_instance - skip validation since they're user-provided
    SKIP_VALIDATION = {'host', 'username', 'password'}

    # Now validate each field's actual default against expected
    failures = []

    for field_name, expected_value in EXPECTED_DEFAULTS.items():
        if field_name in SKIP_VALIDATION:
            continue

        try:
            actual_value = getattr(config, field_name)
        except AttributeError:
            failures.append(f"{field_name}: Field not accessible on config object")
            continue

        # Handle different types of comparisons
        if isinstance(expected_value, dict):
            # For nested objects, recursively check fields
            if not _compare_nested_object(actual_value, expected_value, field_name, failures):
                continue
        elif isinstance(expected_value, (list, tuple)):
            # Convert actual value to same type for comparison
            if isinstance(actual_value, (list, tuple)):
                actual_as_type = type(expected_value)(actual_value)
                if actual_as_type != expected_value:
                    failures.append(
                        f"{field_name}: expected {expected_value!r}, got {actual_value!r}"
                    )
            elif actual_value is None:
                failures.append(
                    f"{field_name}: expected {expected_value!r}, got None"
                )
            else:
                failures.append(
                    f"{field_name}: expected {expected_value!r}, got {actual_value!r}"
                )
        else:
            # Simple value comparison
            if actual_value != expected_value:
                failures.append(
                    f"{field_name}: expected {expected_value!r}, got {actual_value!r}"
                )

    if failures:
        error_msg = (
            f"\n\n{'=' * 80}\n"
            f"DEFAULT VALUE MISMATCHES DETECTED!\n"
            f"{'=' * 80}\n\n"
            f"The following fields have default values that don't match expectations:\n\n"
            + "\n".join(f"  • {failure}" for failure in failures) +
            f"\n\n"
            f"This indicates either:\n"
            f"  1. A regression in default values (BAD - investigate carefully!)\n"
            f"  2. EXPECTED_DEFAULTS needs to be updated to match new behavior\n\n"
            f"{'=' * 80}\n"
        )
        pytest.fail(error_msg)


def _compare_nested_object(actual_obj, expected_dict, field_path, failures):
    """
    Recursively compare a nested config object against expected dictionary.

    Returns True if all comparisons passed, False if any failed (failures list is updated).
    """
    all_passed = True

    for key, expected_value in expected_dict.items():
        try:
            actual_value = getattr(actual_obj, key)
        except AttributeError:
            failures.append(f"{field_path}.{key}: Field not accessible")
            all_passed = False
            continue

        if isinstance(expected_value, dict):
            # Recursively check nested objects
            if not _compare_nested_object(actual_value, expected_value, f"{field_path}.{key}", failures):
                all_passed = False
        elif isinstance(expected_value, (list, tuple)):
            # Convert actual value to same type for comparison
            if isinstance(actual_value, (list, tuple)):
                actual_as_type = type(expected_value)(actual_value)
                if actual_as_type != expected_value:
                    failures.append(
                        f"{field_path}.{key}: expected {expected_value!r}, got {actual_value!r}"
                    )
                    all_passed = False
            elif actual_value is None:
                failures.append(
                    f"{field_path}.{key}: expected {expected_value!r}, got None"
                )
                all_passed = False
            else:
                failures.append(
                    f"{field_path}.{key}: expected {expected_value!r}, got {actual_value!r}"
                )
                all_passed = False
        else:
            # Simple value comparison
            if actual_value != expected_value:
                failures.append(
                    f"{field_path}.{key}: expected {expected_value!r}, got {actual_value!r}"
                )
                all_passed = False

    return all_passed
