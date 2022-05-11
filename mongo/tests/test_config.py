# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.mongo.config import MongoConfig


def test_badly_formatted_server(instance):
    instance['hosts'] = ['sandbox.foo.bar.mongodb.com\\:27017\\']
    with pytest.raises(ConfigurationError, match='Could not build a mongo uri with the given hosts'):
        MongoConfig(instance, mock.Mock())


def test_deprecated_schema(instance):
    instance['hosts'] = ['mongodb+srv://sandbox.foo.bar.mongodb.com:27017']
    with pytest.raises(ConfigurationError, match='Could not build a mongo uri with the given hosts'):
        MongoConfig(instance, mock.Mock())
