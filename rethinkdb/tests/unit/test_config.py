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
    instance = {}  # type: Instance
    config = Config(instance)
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


def test_config_repr():
    # type: () -> None
    instance = {}  # type: Instance
    config = Config(instance)
    assert repr(config) == "Config(host='localhost', port=28015, user=None, password='', tls_ca_cert=None, tags=[])"


@pytest.mark.parametrize('host', [42, True, object()])
def test_invalid_host(host):
    # type: (Any) -> None
    with pytest.raises(ConfigurationError):
        Config(instance={'host': host})


@pytest.mark.parametrize('port', [42.42, -42, True, object()])
def test_invalid_port(port):
    # type: (Any) -> None
    with pytest.raises(ConfigurationError):
        Config(instance={'port': port})
