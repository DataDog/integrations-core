# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.rethinkdb.config import Config
from datadog_checks.rethinkdb.types import Instance

pytestmark = pytest.mark.unit


def test_default_config():
    # type: () -> None
    config = Config()
    assert config.host == 'localhost'
    assert config.port == 28015
    assert config.user is None
    assert config.tls_ca_cert is None
    assert config.tags == []


def test_config():
    # type: () -> None
    instance = {
        'host': '192.168.121.1',
        'port': 28016,
        'username': 'datadog-agent',
        'password': 's3kr3t',
        'tls_ca_cert': '/path/to/client.cert',
        'tags': ['env:testing'],
    }  # type: Instance
    config = Config(instance)
    assert config.host == '192.168.121.1'
    assert config.port == 28016
    assert config.user == 'datadog-agent'
    assert config.tls_ca_cert == '/path/to/client.cert'
    assert config.tags == ['env:testing']


@pytest.mark.parametrize('value', [42, True, object()])
def test_invalid_host(value):
    # type: (Any) -> None
    with pytest.raises(ConfigurationError):
        Config(instance={'host': value})


@pytest.mark.parametrize('value', [42.42, -42, True, object()])
def test_invalid_port(value):
    # type: (Any) -> None
    with pytest.raises(ConfigurationError):
        Config(instance={'port': value})


@pytest.mark.parametrize('value', ['not-a-number', object()])
def test_invalid_min_collection_interval(value):
    # type: (Any) -> None
    with pytest.raises(ConfigurationError):
        Config(instance={'min_collection_interval': value})
