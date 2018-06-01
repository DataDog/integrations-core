# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import pytest


@pytest.mark.unit
def test_parse_counter(aggregator, squid_check):
    # Good format
    line = "counter = 0\n"
    counter, value = squid_check.parse_counter(line)
    assert counter == "counter"
    assert value == "0"

    # Bad format
    line = "counter: value\n"
    counter, value = squid_check.parse_counter(line)
    assert counter is None
    assert value is None


@pytest.mark.unit
def test_parse_instance(aggregator, squid_check):
    # instance with defaults
    instance = {
        "name": "ok_instance"
    }
    name, host, port, cachemgr_user, \
        cachemgr_passwd, custom_tags = squid_check.parse_instance(instance)
    assert name == "ok_instance"
    assert host == "localhost"
    assert port == 3128
    assert cachemgr_user == ""
    assert cachemgr_passwd == ""
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
    name, host, port, cachemgr_user,\
        cachemgr_passwd, custom_tags = squid_check.parse_instance(instance)
    assert name == "ok_instance"
    assert host == "host"
    assert port == 1234
    assert cachemgr_user == "datadog"
    assert cachemgr_passwd == "pass"
    assert custom_tags == ["foo:bar"]

    # instance with no name
    instance = {
        "host": "host"
    }
    with pytest.raises(Exception):
        squid_check.parse_instance(instance)


@pytest.mark.unit
def test_get_counters(squid_check):
    """
    Squid can return a trailing newline at the end of its metrics and it would be
    treated as a metric line: an error would be raised attempting to parse the line
    due to a missing = character.
    See https://github.com/DataDog/integrations-core/pull/1643
    """
    with mock.patch('datadog_checks.squid.squid.requests.get') as g:
        g.return_value = mock.MagicMock(text="client_http.requests=42\n\n")
        squid_check.parse_counter = mock.MagicMock(return_value=('foo', 'bar'))
        squid_check.get_counters('host', 'port', 'user', 'pass', [])
        # we assert `parse_counter` was called only once despite the raw text
        # containing multiple `\n` chars
        squid_check.parse_counter.assert_called_once()
