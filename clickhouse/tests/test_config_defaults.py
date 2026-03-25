# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""
The goal of these tests is to verify our default configuration values are correct and remain consistent.
Failing tests indicate a regression in our defaults and should be inspected carefully.
Default values are duplicated within this file by design to ensure tests fail if the value changes unexpectedly.
"""

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.config_models.instance import InstanceConfig

# Single source of truth for all expected default values.
# Organized by category for readability.
# These values are intentionally duplicated from defaults.py / dict_defaults.py so that
# any change to either source breaks this test and forces a conscious review.
EXPECTED_DEFAULTS = {
    # === Required fields (no defaults) ===
    'server': None,  # Required — provided by the minimal instance fixture
    # === Connection configuration ===
    # Note: old inline code had port=None (no default). New default is 8123,
    # which matches ClickHouse's documented HTTP port and is functionally equivalent.
    'port': 8123,
    'db': 'default',
    'username': 'default',
    # Note: old inline code defaulted to ''. Fixed in #23015 after the Pydantic
    # refactor accidentally defaulted to None, causing auth error 194.
    'password': '',
    'connect_timeout': 10,
    'read_timeout': 10,
    # Note: old inline code defaulted to False (bool). New default is None,
    # which is coerced to False in connect() via `compression if compression else False`.
    # coerce_bool(None) == coerce_bool(False) == False in clickhouse_connect — no behaviour change.
    'compression': None,
    'tls_verify': False,
    'tls_ca_cert': None,
    'verify': True,
    # === Database identifier ===
    'database_identifier': {
        'template': '$server:$port:$db',
    },
    # === DBM toggle ===
    'dbm': False,
    'single_endpoint_mode': False,
    # === DBM: Query metrics ===
    'query_metrics': {
        'enabled': True,
        'collection_interval': 10,
        'run_sync': False,
        'full_statement_text_cache_max_size': 10000,
        'full_statement_text_samples_per_hour_per_query': 1,
    },
    # === DBM: Query samples ===
    'query_samples': {
        'enabled': True,
        'collection_interval': 1,
        'payload_row_limit': 1000,
        'run_sync': False,
    },
    # === DBM: Query completions ===
    'query_completions': {
        'enabled': True,
        'collection_interval': 10,
        'samples_per_hour_per_query': 15,
        'seen_samples_cache_maxsize': 10000,
        'max_samples_per_collection': 1000,
        'run_sync': False,
    },
    # === Tagging ===
    'tags': (),
    'disable_generic_tags': False,
    'enable_legacy_tags_normalization': True,
    # === Custom queries ===
    'custom_queries': None,
    'only_custom_queries': False,
    'use_global_custom_queries': 'true',
    # === Agent standard fields ===
    'min_collection_interval': 15,
    'empty_default_hostname': False,
    # === User-provided / no default ===
    'service': None,
    'metric_patterns': None,
}

pytestmark = pytest.mark.unit


@pytest.fixture
def minimal_instance():
    """Minimal instance configuration with only the required field."""
    return {'server': 'localhost'}


def test_all_config_defaults(minimal_instance):
    """
    Verify that all InstanceConfig fields have the expected default values when only
    the required 'server' field is provided.

    If a field is missing from EXPECTED_DEFAULTS the test fails with instructions on how to fix it.
    Failures on existing fields indicate a potential config regression for existing users.
    """
    check = ClickhouseCheck('clickhouse', {}, [minimal_instance])
    config = check._config

    all_fields = set(InstanceConfig.__annotations__.keys())

    missing_from_expected = all_fields - set(EXPECTED_DEFAULTS.keys())
    if missing_from_expected:
        pytest.fail(
            f"\n\n{'=' * 80}\n"
            f"MISSING EXPECTED DEFAULTS!\n"
            f"{'=' * 80}\n\n"
            f"The following fields exist in InstanceConfig but are missing from EXPECTED_DEFAULTS:\n"
            f"  {sorted(missing_from_expected)}\n\n"
            f"To fix this, add each field to EXPECTED_DEFAULTS in test_config_defaults.py\n"
            f"with its expected default value. Examples:\n"
            f"  - Simple field:   'field_name': default_value,\n"
            f"  - No default:     'field_name': None,\n"
            f"  - Nested object:  'field_name': {{'key': 'value'}},\n"
            f"{'=' * 80}\n"
        )

    extra_in_expected = set(EXPECTED_DEFAULTS.keys()) - all_fields
    if extra_in_expected:
        pytest.fail(
            f"\n\nThe following fields are in EXPECTED_DEFAULTS but don't exist in InstanceConfig:\n"
            f"  {sorted(extra_in_expected)}\n"
            f"Remove them from EXPECTED_DEFAULTS in test_config_defaults.py."
        )

    failures = []

    for field_name, expected_value in EXPECTED_DEFAULTS.items():
        if field_name == 'server':
            # Required field provided by the fixture — skip default check
            continue

        actual_value = getattr(config, field_name)

        if isinstance(expected_value, dict):
            _compare_nested_object(actual_value, expected_value, field_name, failures)
        elif isinstance(expected_value, (list, tuple)):
            if isinstance(actual_value, (list, tuple)):
                if type(expected_value)(actual_value) != expected_value:
                    failures.append(f"{field_name}: expected {expected_value!r}, got {actual_value!r}")
            elif actual_value is None:
                failures.append(f"{field_name}: expected {expected_value!r}, got None")
            else:
                failures.append(f"{field_name}: expected {expected_value!r}, got {actual_value!r}")
        else:
            if actual_value != expected_value:
                failures.append(f"{field_name}: expected {expected_value!r}, got {actual_value!r}")

    if failures:
        pytest.fail(
            f"\n\n{'=' * 80}\n"
            f"DEFAULT VALUE MISMATCHES DETECTED!\n"
            f"{'=' * 80}\n\n"
            f"The following fields have unexpected default values:\n\n"
            + "\n".join(f"  • {f}" for f in failures)
            + f"\n\n"
            f"This indicates either:\n"
            f"  1. A regression in default values (BAD — investigate carefully!)\n"
            f"  2. EXPECTED_DEFAULTS needs updating to reflect intentional new behaviour\n"
            f"{'=' * 80}\n"
        )


def _compare_nested_object(actual_obj, expected_dict, field_path, failures):
    """Recursively compare a nested config object against an expected dict."""
    for key, expected_value in expected_dict.items():
        try:
            actual_value = getattr(actual_obj, key)
        except AttributeError:
            failures.append(f"{field_path}.{key}: field not accessible on config object")
            continue

        if isinstance(expected_value, dict):
            _compare_nested_object(actual_value, expected_value, f"{field_path}.{key}", failures)
        elif isinstance(expected_value, (list, tuple)):
            if isinstance(actual_value, (list, tuple)):
                if type(expected_value)(actual_value) != expected_value:
                    failures.append(f"{field_path}.{key}: expected {expected_value!r}, got {actual_value!r}")
            elif actual_value is None:
                failures.append(f"{field_path}.{key}: expected {expected_value!r}, got None")
            else:
                failures.append(f"{field_path}.{key}: expected {expected_value!r}, got {actual_value!r}")
        else:
            if actual_value != expected_value:
                failures.append(f"{field_path}.{key}: expected {expected_value!r}, got {actual_value!r}")
