# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.ibm_mq.config import IBMMQConfig

from .common import HOST

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    'override_hostname, expected_hostname, expected_tag',
    [(False, None, 'mq_host:{}'.format(HOST)), (True, HOST, None)],
)
def test_mq_host_tag(instance, override_hostname, expected_hostname, expected_tag):
    instance['override_hostname'] = override_hostname
    config = IBMMQConfig(instance)

    assert config.hostname == expected_hostname
    if expected_tag:
        assert expected_tag in config.tags


def test_cannot_set_host_and_connection_name(instance):
    instance['connection_name'] = "localhost(8080)"
    with pytest.raises(ConfigurationError, match="Specify only one host/port or connection_name configuration"):
        IBMMQConfig(instance)


def test_cannot_set_override_hostname_and_connection_name(instance):
    instance['connection_name'] = "localhost(8080)"
    del instance['host']
    del instance['port']
    instance['override_hostname'] = True
    with pytest.raises(
        ConfigurationError, match="You cannot override the hostname if you provide a connection_name instead of a host"
    ):
        IBMMQConfig(instance)
