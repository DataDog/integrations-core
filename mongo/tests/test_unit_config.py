# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.mongo import MongoDb
from datadog_checks.mongo.config import MongoConfig


def test_none_hosts():
    instance = {}
    with pytest.raises(ConfigurationError, match='No `hosts` specified'):
        MongoConfig(instance, mock.Mock(), {})


def test_empty_hosts():
    instance = {'hosts': []}
    with pytest.raises(ConfigurationError, match='No `hosts` specified'):
        MongoConfig(instance, mock.Mock(), {})


def test_default_tls_params():
    instance = {'hosts': ['test.mongodb.com']}
    config = MongoConfig(instance, mock.Mock(), {})
    assert config.tls_params == {}


def test_default_scheme(instance):
    instance['hosts'] = ['test.mongodb.com']
    with mock.patch('pymongo.uri_parser.parse_uri', return_value={'nodelist': ["test.mongodb.com"]}) as mock_parse_uri:
        MongoConfig(instance, mock.Mock(), {})
        mock_parse_uri.assert_called_once_with("mongodb://test.mongodb.com/")


def test_invalid_scheme(instance):
    instance['hosts'] = ['sandbox.foo.bar.mongodb.com']
    instance['connection_scheme'] = 'invalid'
    with pytest.raises(ConfigurationError, match='Could not build a mongo uri with the given hosts'):
        MongoConfig(instance, mock.Mock(), {})


def test_mongodb_scheme(instance):
    instance['hosts'] = ['test.mongodb.com']
    instance['connection_scheme'] = 'mongodb'
    with mock.patch('pymongo.uri_parser.parse_uri', return_value={'nodelist': ["test.mongodb.com"]}) as mock_parse_uri:
        MongoConfig(instance, mock.Mock(), {})
        mock_parse_uri.assert_called_once_with("mongodb://test.mongodb.com/")


def test_mongodb_srv_scheme(instance):
    instance['hosts'] = ['test.mongodb.com']
    instance['connection_scheme'] = 'mongodb+srv'
    with mock.patch(
        'pymongo.uri_parser.parse_uri', return_value={'nodelist': ["resolved.mongodb.com"]}
    ) as mock_parse_uri:
        MongoConfig(instance, mock.Mock(), {})
        mock_parse_uri.assert_called_once_with("mongodb+srv://test.mongodb.com/")


def test_badly_formatted_server(instance):
    instance['hosts'] = ['sandbox.foo.bar.mongodb.com\\:27017\\']
    with pytest.raises(ConfigurationError, match='Could not build a mongo uri with the given hosts'):
        MongoConfig(instance, mock.Mock(), {})


def test_hosts_can_be_singular(instance):
    instance['hosts'] = 'localfoost'
    check = MongoDb('mongo_check', {}, instances=[instance])
    assert check._config.hosts == ['localfoost']

    check.load_configuration_models()
    assert check._config_model_instance.hosts == ('localfoost',)


def test_dbnames_not_exists(instance):
    config = MongoConfig(instance, mock.Mock(), {})
    assert config.db_names is None


def test_dbnames_empty(instance):
    instance['dbnames'] = []
    config = MongoConfig(instance, mock.Mock(), {})
    assert config.db_names == []


def test_dbnames_non_empty(instance):
    instance['dbnames'] = ['test']
    config = MongoConfig(instance, mock.Mock(), {})
    assert config.db_names == ['test']


def test_custom_replicaSet_is_not_allowed(instance):
    instance['options'] = {'replicaSet': 'foo'}
    with pytest.raises(ConfigurationError, match='replicaSet'):
        MongoConfig(instance, mock.Mock(), {})


def test_dbm_cluster_name(instance):
    instance['dbm'] = True
    with pytest.raises(ConfigurationError, match='`cluster_name` must be set when `dbm` is enabled'):
        MongoConfig(instance, mock.Mock(), {})


@pytest.mark.parametrize(
    'dbm_enabled, operation_samples_config, operation_samples_enabled',
    [
        pytest.param(True, None, True, id='dbm_enabled_default'),
        pytest.param(True, {'enabled': True}, True, id='operation_samples_enabled'),
        pytest.param(True, {'enabled': False}, False, id='operation_samples_disabled'),
        pytest.param(False, None, False, id='dbm_disabled_default'),
        pytest.param(False, {'enabled': True}, False, id='operation_samples_enabled_dbm_disabled'),
        pytest.param(False, {'enabled': False}, False, id='operation_samples_disabled_dbm_disabled'),
    ],
)
def test_mongo_operation_samples_enabled(
    instance_integration_cluster, check, dbm_enabled, operation_samples_config, operation_samples_enabled
):
    instance_integration_cluster['dbm'] = dbm_enabled
    if operation_samples_config:
        instance_integration_cluster['operation_samples'] = operation_samples_config

    mongo_check = check(instance_integration_cluster)
    assert mongo_check._config.operation_samples.get('enabled') == operation_samples_enabled


@pytest.mark.parametrize(
    'dbm_enabled, slow_operations_config, slow_operations_enabled',
    [
        pytest.param(True, None, True, id='dbm_enabled_default'),
        pytest.param(True, {'enabled': True}, True, id='slow_operations_enabled'),
        pytest.param(True, {'enabled': False}, False, id='slow_operations_disabled'),
        pytest.param(False, None, False, id='dbm_disabled_default'),
        pytest.param(False, {'enabled': True}, False, id='slow_operations_enabled_dbm_disabled'),
        pytest.param(False, {'enabled': False}, False, id='slow_operations_disabled_dbm_disabled'),
    ],
)
def test_mongo_slow_operations_enabled(
    instance_integration_cluster, check, dbm_enabled, slow_operations_config, slow_operations_enabled
):
    instance_integration_cluster['dbm'] = dbm_enabled
    if slow_operations_config:
        instance_integration_cluster['slow_operations'] = slow_operations_config

    mongo_check = check(instance_integration_cluster)
    assert mongo_check._config.slow_operations.get('enabled') == slow_operations_enabled


def test_database_autodiscovery_disabled(instance_user):
    config = MongoConfig(instance_user, mock.Mock(), {})
    assert config.database_autodiscovery_config is not None
    assert config.database_autodiscovery_config['enabled'] is False


def test_database_autodiscovery_enabled(instance_user):
    instance_user['database_autodiscovery'] = {'enabled': True, 'include': ['test.*'], 'exclude': ['admin']}
    config = MongoConfig(instance_user, mock.Mock(), {})
    assert config.database_autodiscovery_config is not None
    assert config.database_autodiscovery_config['enabled'] is True
    assert config.database_autodiscovery_config['include'] == ['test.*']
    assert config.database_autodiscovery_config['exclude'] == ['admin']


def test_database_autodiscovery_dbnames_deprecation(instance_user):
    # dbnames is deprecated in favor of database_autodiscovery
    # for backwards compatibility, we implicitly enable database_autodiscovery if dbnames is set
    # and set the include list to the dbnames list
    instance_user['dbnames'] = ['test', 'integration']
    config = MongoConfig(instance_user, mock.Mock(), {})
    assert config.database_autodiscovery_config is not None
    assert config.database_autodiscovery_config['enabled'] is True
    assert config.database_autodiscovery_config['include'] == ['test$', 'integration$']


@pytest.mark.parametrize(
    'aws_cloud_metadata',
    [
        pytest.param(
            {
                'instance_endpoint': 'mycluster.cluster-123456789012.us-east-1.docdb.amazonaws.com',
                'cluster_identifier': 'mydocdbcluster',
            },
            id='aws_cloud_metadata',
        ),
        pytest.param(
            {'instance_endpoint': 'mycluster.cluster-123456789012.us-east-1.docdb.amazonaws.com'},
            id='aws_cloud_metadata_no_cluster_identifier',
        ),
    ],
)
def test_amazon_docdb_cloud_metadata(instance_integration_cluster, aws_cloud_metadata):
    instance_integration_cluster['aws'] = aws_cloud_metadata
    config = MongoConfig(instance_integration_cluster, mock.Mock(), {})
    assert config.cloud_metadata is not None
    aws = config.cloud_metadata['aws']
    assert aws['instance_endpoint'] == aws_cloud_metadata['instance_endpoint']
    assert aws['cluster_identifier'] is not None
    if 'cluster_identifier' in aws_cloud_metadata:
        assert aws['cluster_identifier'] == aws_cloud_metadata['cluster_identifier']
    else:
        assert aws['cluster_identifier'] == instance_integration_cluster['cluster_name']


@pytest.mark.parametrize(
    'metrics_collection_interval, expected_metrics_collection_interval',
    [
        pytest.param(
            {}, {'collection': 15, 'collections_indexes_stats': 15, 'sharded_data_distribution': 300}, id='default'
        ),
        pytest.param(
            {
                'collection': '60',
                'collections_indexes_stats': '30',
                'sharded_data_distribution': '600',
            },
            {'collection': 60, 'collections_indexes_stats': 30, 'sharded_data_distribution': 600},
            id='custom',
        ),
        pytest.param(
            {
                'collection': 60,
            },
            {'collection': 60, 'collections_indexes_stats': 15, 'sharded_data_distribution': 300},
            id='partial',
        ),
    ],
)
def test_metrics_collection_interval(instance, metrics_collection_interval, expected_metrics_collection_interval):
    instance['metrics_collection_interval'] = metrics_collection_interval
    config = MongoConfig(instance, mock.Mock(), {})
    assert config.metrics_collection_interval == expected_metrics_collection_interval
