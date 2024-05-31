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
        MongoConfig(instance, mock.Mock())


def test_empty_hosts():
    instance = {'hosts': []}
    with pytest.raises(ConfigurationError, match='No `hosts` specified'):
        MongoConfig(instance, mock.Mock())


def test_default_tls_params():
    instance = {'hosts': ['test.mongodb.com']}
    config = MongoConfig(instance, mock.Mock())
    assert config.tls_params == {}


def test_default_scheme(instance):
    instance['hosts'] = ['test.mongodb.com']
    with mock.patch('pymongo.uri_parser.parse_uri', return_value={'nodelist': ["test.mongodb.com"]}) as mock_parse_uri:
        MongoConfig(instance, mock.Mock())
        mock_parse_uri.assert_called_once_with("mongodb://test.mongodb.com/")


def test_invalid_scheme(instance):
    instance['hosts'] = ['sandbox.foo.bar.mongodb.com']
    instance['connection_scheme'] = 'invalid'
    with pytest.raises(ConfigurationError, match='Could not build a mongo uri with the given hosts'):
        MongoConfig(instance, mock.Mock())


def test_mongodb_scheme(instance):
    instance['hosts'] = ['test.mongodb.com']
    instance['connection_scheme'] = 'mongodb'
    with mock.patch('pymongo.uri_parser.parse_uri', return_value={'nodelist': ["test.mongodb.com"]}) as mock_parse_uri:
        MongoConfig(instance, mock.Mock())
        mock_parse_uri.assert_called_once_with("mongodb://test.mongodb.com/")


def test_mongodb_srv_scheme(instance):
    instance['hosts'] = ['test.mongodb.com']
    instance['connection_scheme'] = 'mongodb+srv'
    with mock.patch(
        'pymongo.uri_parser.parse_uri', return_value={'nodelist': ["resolved.mongodb.com"]}
    ) as mock_parse_uri:
        MongoConfig(instance, mock.Mock())
        mock_parse_uri.assert_called_once_with("mongodb+srv://test.mongodb.com/")


def test_badly_formatted_server(instance):
    instance['hosts'] = ['sandbox.foo.bar.mongodb.com\\:27017\\']
    with pytest.raises(ConfigurationError, match='Could not build a mongo uri with the given hosts'):
        MongoConfig(instance, mock.Mock())


def test_hosts_can_be_singular(instance):
    instance['hosts'] = 'localfoost'
    check = MongoDb('mongo_check', {}, instances=[instance])
    assert check._config.hosts == ['localfoost']

    check.load_configuration_models()
    assert check._config_model_instance.hosts == ('localfoost',)


def test_dbnames_not_exists(instance):
    config = MongoConfig(instance, mock.Mock())
    assert config.db_names is None


def test_dbnames_empty(instance):
    instance['dbnames'] = []
    config = MongoConfig(instance, mock.Mock())
    assert config.db_names == []


def test_dbnames_non_empty(instance):
    instance['dbnames'] = ['test']
    config = MongoConfig(instance, mock.Mock())
    assert config.db_names == ['test']


def test_custom_replicaSet_is_not_allowed(instance):
    instance['options'] = {'replicaSet': 'foo'}
    with pytest.raises(ConfigurationError, match='replicaSet'):
        MongoConfig(instance, mock.Mock())


def test_dbm_cluster_name(instance):
    instance['dbm'] = True
    with pytest.raises(ConfigurationError, match='`cluster_name` must be set when `dbm` is enabled'):
        MongoConfig(instance, mock.Mock())


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
