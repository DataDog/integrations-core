# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from copy import deepcopy

import mock
import pytest

from datadog_checks.squid import SquidCheck

from . import common


def test_parse_counter(aggregator, check):
    # Good format
    line = "counter = 0\n"
    counter, value = check.parse_counter(line)
    assert counter == "counter"
    assert value == "0"

    # Bad format
    line = "counter: value\n"
    counter, value = check.parse_counter(line)
    assert counter is None
    assert value is None


def test_parse_instance(aggregator, check):
    # instance with defaults
    instance = {"name": "ok_instance"}
    name, host, port, custom_tags = check.parse_instance(instance)
    assert name == "ok_instance"
    assert host == "localhost"
    assert port == 3128
    assert custom_tags == []

    # instance with no defaults
    instance = {
        "name": "ok_instance",
        "host": "host",
        "port": 1234,
        "cachemgr_username": "datadog",
        "cachemgr_password": "pass",
        "tags": ["foo:bar"],
    }
    name, host, port, custom_tags = check.parse_instance(instance)
    assert name == "ok_instance"
    assert host == "host"
    assert port == 1234
    assert custom_tags == ["foo:bar"]

    # instance with no name
    instance = {"host": "host"}
    with pytest.raises(Exception):
        check.parse_instance(instance)


def test_get_counters(check):
    """
    Squid can return a trailing newline at the end of its metrics and it would be
    treated as a metric line: an error would be raised attempting to parse the line
    due to a missing = character.
    See https://github.com/DataDog/integrations-core/pull/1643
    """
    with mock.patch('datadog_checks.squid.squid.requests.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            g.return_value = mock.MagicMock(text="client_http.requests=42\n\n")
            check.parse_counter = mock.MagicMock(return_value=('foo', 'bar'))
            check.get_counters('host', 'port', [])
            # we assert `parse_counter` was called only once despite the raw text
            # containing multiple `\n` chars
            check.parse_counter.assert_called_once()


def test_host_without_protocol(check, instance):
    with mock.patch('datadog_checks.squid.squid.requests.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            g.return_value = mock.MagicMock(text="client_http.requests=42\n\n")
            check.parse_counter = mock.MagicMock(return_value=('foo', 'bar'))
            check.check(instance)
            assert g.call_args.args[0] == 'http://localhost:3128/squid-internal-mgr/counters'


def test_host_https(check, instance):
    instance['host'] = 'https://localhost'
    with mock.patch('datadog_checks.squid.squid.requests.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            g.return_value = mock.MagicMock(text="client_http.requests=42\n\n")
            check.parse_counter = mock.MagicMock(return_value=('foo', 'bar'))
            check.check(instance)
            assert g.call_args.args[0] == 'https://localhost:3128/squid-internal-mgr/counters'


@pytest.mark.parametrize(
    'auth_config',
    [
        {"cachemgr_username": "datadog_user", "cachemgr_password": "datadog_pass"},
        {"username": "datadog_user", "password": "datadog_pass"},
    ],
)
def test_legacy_username_password(instance, auth_config):
    instance = deepcopy(instance)
    instance.update(auth_config)
    check = SquidCheck(common.CHECK_NAME, {}, {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests.get') as g:
        with mock.patch('datadog_checks.squid.SquidCheck.submit_version'):
            check.get_counters('host', 'port', [])

            g.assert_called_with(
                'http://host:port/squid-internal-mgr/counters',
                auth=('datadog_user', 'datadog_pass'),
                cert=mock.ANY,
                headers=mock.ANY,
                proxies=mock.ANY,
                timeout=mock.ANY,
                verify=mock.ANY,
                allow_redirects=mock.ANY,
            )
