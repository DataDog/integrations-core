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
