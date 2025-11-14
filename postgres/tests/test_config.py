# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json
from unittest.mock import MagicMock

import pytest

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.postgres.config import (
    FeatureKey,
    ValidationResult,
    build_config,
    deprecation_warning,
    sanitize,
)
from datadog_checks.postgres.config_models import dict_defaults
from datadog_checks.postgres.config_models.instance import Relations
from datadog_checks.postgres.relationsmanager import RelationsManager


@pytest.fixture
def mock_check():
    # Mock check object with a warning method
    check = MagicMock()
    check.warning = MagicMock()
    return check


@pytest.fixture
def minimal_instance():
    return {'host': 'localhost', 'port': 5432, 'username': 'testuser', 'password': 'testpass', 'dbname': 'testdb'}


pytestmark = pytest.mark.unit


def test_initialize_valid_config(mock_check, minimal_instance):
    mock_check.instance = minimal_instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert isinstance(result, ValidationResult)
    assert result.valid
    assert not result.errors


def test_initialize_invalid_ssl_mode(mock_check, minimal_instance):
    instance = minimal_instance
    instance['ssl'] = 'invalid_ssl'
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid  # Should still be valid, but with a warning
    assert any("Invalid ssl option" in w for w in result.warnings)


def test_initialize_conflicting_collect_default_database_and_ignore_databases(mock_check, minimal_instance):
    instance = minimal_instance
    instance['collect_default_database'] = True
    instance['ignore_databases'] = ['postgres']
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid
    assert any("cannot be ignored" in w for w in result.warnings)


def test_initialize_non_ascii_application_name(mock_check, minimal_instance):
    instance = minimal_instance
    instance['application_name'] = 'datadog-агент'
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert not result.valid
    assert any("ASCII characters" in str(e) for e in result.errors)


def test_initialize_features_enabled_and_disabled(mock_check, minimal_instance):
    # Enable all features
    instance = minimal_instance
    instance.update(
        {
            'relations': ['public.table1'],
            'dbm': True,
            'query_samples': {'enabled': True},
            'collect_settings': {'enabled': True},
            'collect_schemas': {'enabled': True},
            'query_activity': {'enabled': True},
            'query_metrics': {'enabled': True},
        }
    )
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    feature_keys = {f['key'] for f in result.features}
    assert set(feature_keys) == {
        FeatureKey.RELATION_METRICS,
        FeatureKey.QUERY_SAMPLES,
        FeatureKey.COLLECT_SETTINGS,
        FeatureKey.COLLECT_SCHEMAS,
        FeatureKey.QUERY_ACTIVITY,
        FeatureKey.QUERY_METRICS,
    }
    for feature in result.features:
        assert feature['enabled'] is True


def test_initialize_features_disabled_by_default(mock_check, minimal_instance):
    mock_check.instance = minimal_instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    features = {f['key']: f for f in result.features}
    assert features[FeatureKey.RELATION_METRICS]['enabled'] is False
    assert features[FeatureKey.QUERY_SAMPLES]['enabled'] is False
    assert features[FeatureKey.COLLECT_SETTINGS]['enabled'] is False
    assert features[FeatureKey.COLLECT_SCHEMAS]['enabled'] is False
    assert features[FeatureKey.QUERY_ACTIVITY]['enabled'] is False
    assert features[FeatureKey.QUERY_METRICS]['enabled'] is False


def test_initialize_features_warn_if_dbm_missing_for_dbm_features(mock_check, minimal_instance):
    # Enable features that require dbm, but do not enable dbm
    instance = minimal_instance
    instance['query_samples'] = {'enabled': True}
    instance['collect_settings'] = {'enabled': True}
    instance['collect_schemas'] = {'enabled': True}
    instance['query_activity'] = {'enabled': True}
    instance['query_metrics'] = {'enabled': True}
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    # Should warn for each feature that requires dbm
    assert any("requires the `dbm` option to be enabled" in w for w in result.warnings)
    # Should have all features in the features list
    feature_keys = {f['key'] for f in result.features}
    assert FeatureKey.QUERY_SAMPLES in feature_keys
    assert FeatureKey.COLLECT_SETTINGS in feature_keys
    assert FeatureKey.COLLECT_SCHEMAS in feature_keys
    assert FeatureKey.QUERY_ACTIVITY in feature_keys
    assert FeatureKey.QUERY_METRICS in feature_keys


def test_initialize_deprecated_options_warn(mock_check, minimal_instance):
    instance = minimal_instance
    instance['deep_database_monitoring'] = True
    instance['statement_samples'] = {'enabled': True}
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert config.dbm is True
    assert any("deprecated" in w for w in result.warnings)


def test_initialize_empty_default_hostname_warns(mock_check, minimal_instance):
    instance = minimal_instance
    instance['empty_default_hostname'] = True
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert any("empty_default_hostname" in w for w in result.warnings)


@pytest.mark.parametrize(
    'instance, init_config, should_propagate',
    [
        (True, True, True),
        (False, False, False),
        (True, False, True),
        (False, True, False),
        (None, True, True),
        (None, False, False),
        (False, None, False),
        (True, None, True),
    ],
)
def test_propagate_agent_tags(instance, init_config, should_propagate, mock_check, minimal_instance):
    minimal_instance['propagate_agent_tags'] = instance
    init_config = {'propagate_agent_tags': init_config}
    mock_check.instance = minimal_instance
    mock_check.init_config = init_config
    config, _ = build_config(check=mock_check)
    assert config.propagate_agent_tags == should_propagate


def test_sanitize_config(mock_check, minimal_instance):
    instance = minimal_instance
    instance['password'] = 'secret'
    instance['ssl_password'] = 'ssl_secret'
    instance['custom_metrics'] = [
        {
            "descriptors": [],
            "metrics": {"count": ["imqs.user.logins", "MONOTONIC"]},
            "query": "select count(did_what) as %s from actionlog where did_what = 'Login';",
            "relation": False,
        }
    ]
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    sanitized = sanitize(config)
    assert sanitized['password'] == '***'
    assert sanitized['ssl_password'] == '***'
    assert 'custom_metrics' not in sanitized


def test_serialize_config(mock_check, minimal_instance):
    instance = minimal_instance
    instance['password'] = 'secret'
    instance['ssl_password'] = 'ssl_secret'
    instance['custom_metrics'] = [
        {
            "descriptors": [],
            "metrics": {"count": ["imqs.user.logins", "MONOTONIC"]},
            "query": "select count(did_what) as %s from actionlog where did_what = 'Login';",
            "relation": False,
        }
    ]
    instance['custom_queries'] = [
        {
            'metric_prefix': 'custom',
            'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
            'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
            'tags': ['query:custom'],
        },
        {
            'metric_prefix': 'another_custom_one',
            'query': "SELECT letter, num FROM (VALUES (97, 'a'), (98, 'b'), (99, 'c')) AS t (num,letter)",
            'columns': [{'name': 'customtag', 'type': 'tag'}, {'name': 'num', 'type': 'gauge'}],
            'tags': ['query:another_custom_one'],
        },
    ]
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    serialized = json.dumps(sanitize(config))
    assert isinstance(serialized, str)
    assert '"password": "***"' in serialized
    assert '"ssl_password": "***"' in serialized


def test_valid_string_numbers(mock_check, minimal_instance):
    instance = minimal_instance
    instance['query_metrics'] = {'collection_interval': '30'}
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid
    assert config.query_metrics.collection_interval == 30


def test_invalid_numbers(mock_check, minimal_instance):
    instance = minimal_instance
    instance['query_metrics'] = {'collection_interval': 'not_a_number'}
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert any("query_metrics.collection_interval must be greater than 0" in w for w in result.warnings)
    assert config.query_metrics.collection_interval == dict_defaults.instance_query_metrics().collection_interval


def test_relations_validation(mock_check, minimal_instance):
    minimal_instance["relations"] = [
        {"relation_regex": ".*", "schemas": ["hello", "hello2"]},
        # Empty schemas means all schemas, even though the first relation matches first.
        {"relation_regex": r"[pP]ersons[-_]?(dup\d)?"},
    ]

    mock_check.instance = minimal_instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.errors == []
    assert result.valid
    assert config.relations == (
        Relations(relation_regex=".*", schemas=("hello", "hello2")),
        # Empty schemas means all schemas, even though the first relation matches first.
        Relations(relation_regex=r"[pP]ersons[-_]?(dup\d)?"),
    )


@pytest.mark.parametrize(
    'section, section_config, expected_collection_interval',
    [
        (
            "query_metrics",
            {"collection_interval": "not_a_number"},
            dict_defaults.instance_query_metrics().collection_interval,
        ),
        ("query_metrics", {"collection_interval": "0"}, dict_defaults.instance_query_metrics().collection_interval),
        ("query_metrics", {"collection_interval": "1"}, 1),
        (
            "query_samples",
            {"collection_interval": "not_a_number"},
            dict_defaults.instance_query_samples().collection_interval,
        ),
        ("query_samples", {"collection_interval": "0"}, dict_defaults.instance_query_samples().collection_interval),
        ("query_samples", {"collection_interval": "1"}, 1),
        (
            "query_activity",
            {"collection_interval": "not_a_number"},
            dict_defaults.instance_query_activity().collection_interval,
        ),
        ("query_activity", {"collection_interval": "0"}, dict_defaults.instance_query_activity().collection_interval),
        ("query_activity", {"collection_interval": "1"}, 1),
    ],
)
def test_apply_validated_defaults(mock_check, minimal_instance, section, section_config, expected_collection_interval):
    instance = minimal_instance
    instance[section] = {**instance.get(section, {}), **section_config}
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid
    assert getattr(config, section).collection_interval == expected_collection_interval


def test_apply_validated_defaults_ssl(mock_check, minimal_instance):
    instance = minimal_instance
    instance['ssl'] = 'invalid_ssl'
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid
    assert config.ssl == "allow"
    assert any("Invalid ssl option" in w for w in result.warnings)


@pytest.mark.parametrize(
    'option, replacement, value',
    [
        ('custom_metrics', 'custom_queries', []),
        ('deep_database_monitoring', 'dbm', True),
        ('managed_identity', 'azure.managed_authentication', {}),
        ('statement_samples', 'query_samples', {}),
        ('collect_default_database', 'postgres', True),
    ],
)
def test_apply_deprecation_warnings(mock_check, minimal_instance, option, replacement, value):
    instance = minimal_instance
    instance[option] = value
    mock_check.instance = instance
    mock_check.init_config = {}
    _, result = build_config(check=mock_check)
    assert result.valid
    assert any(deprecation_warning(option, replacement) in w for w in result.warnings)


def test_cloud_validations(mock_check, minimal_instance):
    # AWS
    instance = minimal_instance
    instance['aws'] = {'region': 'us-east-1'}
    instance['password'] = None
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid
    assert config.aws.managed_authentication.enabled

    # Azure
    instance = minimal_instance
    instance['managed_identity'] = {'client_id': '123'}
    instance['password'] = None
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid
    assert config.azure.managed_authentication.enabled


def test_relations_validation_fails_if_no_relname_or_regex():
    with pytest.raises(ConfigurationError):
        RelationsManager.validate_relations_config([{"relkind": ["i"]}])


def test_relations_validation_fails_if_schemas_is_wrong_type():
    with pytest.raises(ConfigurationError):
        RelationsManager.validate_relations_config([{"relation_name": "person", "schemas": "foo"}])


def test_relations_validation_fails_if_relkind_is_wrong_type():
    with pytest.raises(ConfigurationError):
        RelationsManager.validate_relations_config([{"relation_name": "person", "relkind": "foo"}])


def test_autodiscovery_dbname_defaults_to_global_view_db(mock_check):
    # When autodiscovery is enabled and dbname is not explicitly set,
    # dbname should default to global_view_db
    instance = {
        'host': 'localhost',
        'port': 5432,
        'username': 'testuser',
        'password': 'testpass',
        'database_autodiscovery': {
            'enabled': True,
            'global_view_db': 'main',
        },
    }
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid
    assert config.dbname == 'main'


def test_autodiscovery_dbname_respects_explicit_value(mock_check):
    # When autodiscovery is enabled and dbname IS explicitly set,
    # the explicit value should be used, even if it's in the exclude list
    # This allows users to connect to a database for global operations
    # while excluding it from per-database metric collection
    instance = {
        'host': 'localhost',
        'port': 5432,
        'username': 'testuser',
        'password': 'testpass',
        'dbname': 'postgres',
        'database_autodiscovery': {
            'enabled': True,
            'global_view_db': 'postgres',
            'exclude': ['postgres'],
        },
    }
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    # Should be valid - user explicitly set dbname, so they know what they're doing
    assert result.valid
    assert config.dbname == 'postgres'


def test_autodiscovery_excluded_default_dbname_fails(mock_check):
    # When autodiscovery is enabled, default dbname postgres is used,
    # and postgres is in the exclude list, should fail validation
    instance = {
        'host': 'localhost',
        'port': 5432,
        'username': 'testuser',
        'password': 'testpass',
        'database_autodiscovery': {
            'enabled': True,
            'exclude': ['postgres'],
        },
    }
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert not result.valid
    assert any('is excluded by autodiscovery pattern' in str(e) for e in result.errors)
    assert any('global_view_db' in str(e) for e in result.errors)


def test_autodiscovery_with_regex_exclude_pattern(mock_check):
    # Test that regex patterns work correctly in exclude validation
    instance = {
        'host': 'localhost',
        'port': 5432,
        'username': 'testuser',
        'password': 'testpass',
        'database_autodiscovery': {
            'enabled': True,
            'global_view_db': 'test_main',
            'exclude': ['test_.*'],
        },
    }
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert not result.valid
    assert any('is excluded by autodiscovery pattern' in str(e) for e in result.errors)


def test_autodiscovery_with_non_excluded_global_view_db_succeeds(mock_check):
    # When autodiscovery is enabled with exclude patterns,
    # but global_view_db doesn't match any of them, should succeed
    instance = {
        'host': 'localhost',
        'port': 5432,
        'username': 'testuser',
        'password': 'testpass',
        'database_autodiscovery': {
            'enabled': True,
            'global_view_db': 'production',
            'exclude': ['postgres', 'test_.*'],
        },
    }
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert result.valid
    assert config.dbname == 'production'


def test_autodiscovery_case_insensitive_exclude_matching(mock_check):
    # Exclude patterns should be case-insensitive
    instance = {
        'host': 'localhost',
        'port': 5432,
        'username': 'testuser',
        'password': 'testpass',
        'database_autodiscovery': {
            'enabled': True,
            'global_view_db': 'POSTGRES',
            'exclude': ['postgres'],
        },
    }
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    assert not result.valid
    assert any('is excluded by autodiscovery pattern' in str(e) for e in result.errors)


def test_autodiscovery_invalid_regex_pattern_warns(mock_check):
    # Invalid regex patterns should generate warnings
    instance = {
        'host': 'localhost',
        'port': 5432,
        'username': 'testuser',
        'password': 'testpass',
        'database_autodiscovery': {
            'enabled': True,
            'global_view_db': 'main',
            'exclude': ['[invalid'],  # Invalid regex
        },
    }
    mock_check.instance = instance
    mock_check.init_config = {}
    config, result = build_config(check=mock_check)
    # Should have a warning about invalid regex
    assert any('Invalid regex pattern' in w for w in result.warnings)
