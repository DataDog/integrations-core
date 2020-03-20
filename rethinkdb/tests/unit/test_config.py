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


@pytest.mark.parametrize('port_28016,', [28016, '28016'])
@pytest.mark.parametrize('min_collection_interval_10', [10, '10', '10.0'])
def test_config(port_28016, min_collection_interval_10):
    # type: (Any, Any) -> None
    instance = {
        'host': '192.168.121.1',
        'port': port_28016,
        'username': 'datadog-agent',
        'password': 's3kr3t',
        'tls_ca_cert': '/path/to/client.cert',
        'tags': ['env:testing'],
        'min_collection_interval': min_collection_interval_10,
    }  # type: Instance

    config = Config(instance)
    assert config.host == '192.168.121.1'
    assert config.port == 28016
    assert config.user == 'datadog-agent'
    assert config.tls_ca_cert == '/path/to/client.cert'
    assert config.tags == ['env:testing']
    assert config.min_collection_interval == 10


@pytest.mark.parametrize('value', [42, True, object()])
def test_invalid_host(value):
    # type: (Any) -> None
    with pytest.raises(ConfigurationError):
        Config(instance={'host': value})


@pytest.mark.parametrize('value', [-28016, '280.16', 'true', object()])
def test_invalid_port(value):
    # type: (Any) -> None
    with pytest.raises(ConfigurationError):
        Config(instance={'port': value})


@pytest.mark.parametrize('value', ['not-a-number', object()])
def test_invalid_min_collection_interval(value):
    # type: (Any) -> None
    with pytest.raises(ConfigurationError):
        Config(instance={'min_collection_interval': value})
