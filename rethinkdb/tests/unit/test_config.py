# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.rethinkdb._config import Config
from datadog_checks.rethinkdb._default_metrics import DEFAULT_METRIC_GROUPS

pytestmark = pytest.mark.unit


def test_default_config():
    # type: () -> None
    config = Config(instance={})
    assert config.host == 'localhost'
    assert config.port == 28015


def test_config():
    # type: () -> None
    config = Config(instance={'host': '192.168.121.1', 'port': 28016})
    assert config.host == '192.168.121.1'
    assert config.port == 28016


def test_config_repr():
    # type: () -> None
    config = Config(instance={})
    assert repr(config) == "Config(host='localhost', port=28015)"


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


def test_default_metrics():
    # type: () -> None
    config = Config(instance={})
    default_metric_streams = config.metric_streams
    assert default_metric_streams == list(DEFAULT_METRIC_GROUPS.values())

    config = Config(instance={'default_metrics': True})
    assert config.metric_streams == default_metric_streams

    config = Config(instance={'default_metrics': False})
    assert config.metric_streams == []

    config = Config(instance={'default_metrics': {}})
    assert config.metric_streams == []

    config = Config(instance={'default_metrics': {'table_statistics': True, 'server_statistics': False}})
    assert config.metric_streams == [DEFAULT_METRIC_GROUPS['table_statistics']]

    with pytest.raises(ConfigurationError):
        Config(instance={'default_metrics': 'not a dict nor a bool'})  # type: ignore

    with pytest.raises(ConfigurationError):
        Config(instance={'default_metrics': {'unknown_key': True}})  # type: ignore

    with pytest.raises(ConfigurationError):
        Config(instance={'default_metrics': {'table_statistics': 'not a bool'}})  # type: ignore
