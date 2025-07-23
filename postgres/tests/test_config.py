import pytest
from unittest.mock import MagicMock

from datadog_checks.postgres.config import FeatureKey, PostgresConfig, ValidationResult

@pytest.fixture
def mock_check():
    # Mock check object with a warning method
    check = MagicMock()
    check.warning = MagicMock()
    return check

@pytest.fixture
def minimal_instance():
    return {
        'host': 'localhost',
        'port': 5432,
        'username': 'testuser',
        'password': 'testpass',
        'dbname': 'testdb'
    }

pytestmark = pytest.mark.unit

def test_initialize_valid_config(mock_check, minimal_instance):
    config = PostgresConfig(mock_check, {})
    result = config.initialize(minimal_instance)
    assert isinstance(result, ValidationResult)
    assert result.valid
    assert not result.errors

def test_initialize_missing_host(mock_check, minimal_instance):
    instance = minimal_instance.copy()
    instance.pop('host')
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    assert not result.valid
    assert any("Specify a Postgres host" in str(e) for e in result.errors)

def test_initialize_missing_username(mock_check, minimal_instance):
    instance = minimal_instance.copy()
    instance.pop('username')
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    assert not result.valid
    assert any("specify a user" in str(e).lower() for e in result.errors)

def test_initialize_invalid_ssl_mode(mock_check, minimal_instance):
    instance = minimal_instance.copy()
    instance['ssl'] = 'invalid_ssl'
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    assert result.valid  # Should still be valid, but with a warning
    assert any("Invalid ssl option" in w for w in result.warnings)
    mock_check.warning.assert_called()

def test_initialize_conflicting_collect_default_database_and_ignore_databases(mock_check, minimal_instance):
    instance = minimal_instance.copy()
    instance['collect_default_database'] = True
    instance['ignore_databases'] = ['postgres']
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    assert result.valid
    assert any("cannot be ignored" in w for w in result.warnings)

def test_initialize_collect_wal_metrics_without_data_directory(mock_check, minimal_instance):
    instance = minimal_instance.copy()
    instance['collect_wal_metrics'] = True
    instance.pop('data_directory', None)
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    assert not result.valid
    assert any("data_directory" in str(e) for e in result.errors)

def test_initialize_non_ascii_application_name(mock_check, minimal_instance):
    instance = minimal_instance.copy()
    instance['application_name'] = 'datadog-агент'
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    assert not result.valid
    assert any("ASCII characters" in str(e) for e in result.errors)

def test_initialize_features_enabled_and_disabled(mock_check, minimal_instance):
    # Enable all features
    instance = minimal_instance.copy()
    instance.update({
        'relations': ['public.table1'],
        'dbm': True,
        'query_samples': {'enabled': True},
        'collect_settings': {'enabled': True},
        'collect_schemas': {'enabled': True},
        'collect_resources': {'enabled': True},
        'query_activity': {'enabled': True},
        'query_metrics': {'enabled': True},
    })
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    feature_keys = {f['key'] for f in result.features}
    assert set(feature_keys) == {
        FeatureKey.RELATION_METRICS,
        FeatureKey.QUERY_SAMPLES,
        FeatureKey.COLLECT_SETTINGS,
        FeatureKey.COLLECT_SCHEMAS,
        FeatureKey.COLLECT_RESOURCES,
        FeatureKey.QUERY_ACTIVITY,
        FeatureKey.QUERY_METRICS,
    }
    for feature in result.features:
        print(feature)
        assert feature['enabled'] is True

def test_initialize_features_disabled_by_default(mock_check, minimal_instance):
    config = PostgresConfig(mock_check, {})
    result = config.initialize(minimal_instance)
    features = {f['key']: f for f in result.features}
    assert features[FeatureKey.RELATION_METRICS]['enabled'] is False
    assert features[FeatureKey.QUERY_SAMPLES]['enabled'] is False
    assert features[FeatureKey.COLLECT_SETTINGS]['enabled'] is False
    assert features[FeatureKey.COLLECT_SCHEMAS]['enabled'] is False
    assert features[FeatureKey.COLLECT_RESOURCES]['enabled'] is False
    assert features[FeatureKey.QUERY_ACTIVITY]['enabled'] is False
    assert features[FeatureKey.QUERY_METRICS]['enabled'] is False

def test_initialize_features_warn_if_dbm_missing_for_dbm_features(mock_check, minimal_instance):
    # Enable features that require dbm, but do not enable dbm
    instance = minimal_instance.copy()
    instance['query_samples'] = {'enabled': True}
    instance['collect_settings'] = {'enabled': True}
    instance['collect_schemas'] = {'enabled': True}
    instance['collect_resources'] = {'enabled': True}
    instance['query_activity'] = {'enabled': True}
    instance['query_metrics'] = {'enabled': True}
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    # Should warn for each feature that requires dbm
    assert any("requires the `dbm` option to be enabled" in w for w in result.warnings)
    # Should have all features in the features list
    feature_keys = {f['key'] for f in result.features}
    assert FeatureKey.QUERY_SAMPLES in feature_keys
    assert FeatureKey.COLLECT_SETTINGS in feature_keys
    assert FeatureKey.COLLECT_SCHEMAS in feature_keys
    assert FeatureKey.COLLECT_RESOURCES in feature_keys
    assert FeatureKey.QUERY_ACTIVITY in feature_keys
    assert FeatureKey.QUERY_METRICS in feature_keys

def test_initialize_deprecated_options_warn(mock_check, minimal_instance):
    instance = minimal_instance.copy()
    instance['deep_database_monitoring'] = True
    instance['statement_samples'] = {'enabled': True}
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    assert any("deprecated" in w for w in result.warnings)

def test_initialize_empty_default_hostname_warns(mock_check, minimal_instance):
    instance = minimal_instance.copy()
    instance['empty_default_hostname'] = True
    config = PostgresConfig(mock_check, {})
    result = config.initialize(instance)
    assert any("empty_default_hostname" in w for w in result.warnings)
