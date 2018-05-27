# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import common
from datadog_checks.squid import SquidCheck


def test_parse_counter(aggregator):
    squid_check = SquidCheck(common.CHECK_NAME, {}, {})

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


def test_parse_instance(aggregator):
    squid_check = SquidCheck(common.CHECK_NAME, {}, {})

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
