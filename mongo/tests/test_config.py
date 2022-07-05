# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from six import PY2

from datadog_checks.base import ConfigurationError
from datadog_checks.mongo import MongoDb
from datadog_checks.mongo.config import MongoConfig


def test_invalid_scheme(instance):
    instance['hosts'] = ['sandbox.foo.bar.mongodb.com']
    instance['connection_scheme'] = 'invalid'
    with pytest.raises(ConfigurationError, match='Could not build a mongo uri with the given hosts'):
        MongoConfig(instance, mock.Mock())


def test_mongodb_scheme(instance):
    instance['hosts'] = ['localhost']
    instance['connection_scheme'] = 'mongodb'
    MongoConfig(instance, mock.Mock())


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


def test_deprecated_schema(instance):
    instance['hosts'] = ['mongodb+srv://sandbox.foo.bar.mongodb.com:27017']
    with pytest.raises(ConfigurationError, match='Could not build a mongo uri with the given hosts'):
        MongoConfig(instance, mock.Mock())


def test_hosts_can_be_singular(instance):
    instance['hosts'] = 'localfoost'
    check = MongoDb('mongo_check', {}, instances=[instance])
    assert check._config.hosts == ['localfoost']

    if not PY2:
        check.load_configuration_models()
        assert check._config_model_instance.hosts == ('localfoost',)
