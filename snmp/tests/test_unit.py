# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import time

import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev import temp_dir
from datadog_checks.snmp import SnmpCheck
from datadog_checks.snmp.config import InstanceConfig
from datadog_checks.snmp.resolver import OIDTrie

from . import common

pytestmark = pytest.mark.unit


@mock.patch("datadog_checks.snmp.config.hlapi")
def test_parse_metrics(hlapi_mock):
    instance = common.generate_instance_config(common.SUPPORTED_METRIC_TYPES)
    check = SnmpCheck('snmp', {}, [instance])
    # Unsupported metric
    metrics = [{"foo": "bar"}]
    config = InstanceConfig(
        {"ip_address": "127.0.0.1", "community_string": "public", "metrics": [{"OID": "1.2.3", "name": "foo"}]},
        check.warning,
        check.log,
        [],
        None,
        {},
        {},
    )
    hlapi_mock.reset_mock()
    with pytest.raises(Exception):
        config.parse_metrics(metrics, check.warning, check.log)

    # Simple OID
    metrics = [{"OID": "1.2.3", "name": "foo"}]
    table, _, _ = config.parse_metrics(metrics, check.warning, check.log)
    assert len(table) == 1
    hlapi_mock.ObjectIdentity.assert_called_once_with("1.2.3")
    hlapi_mock.reset_mock()

    # MIB with no symbol or table
    metrics = [{"MIB": "foo_mib"}]
    with pytest.raises(Exception):
        config.parse_metrics(metrics, check.warning, check.log)

    # MIB with symbol
    metrics = [{"MIB": "foo_mib", "symbol": "foo"}]
    table, _, _ = config.parse_metrics(metrics, check.warning, check.log)
    assert len(table) == 1
    hlapi_mock.ObjectIdentity.assert_called_once_with("foo_mib", "foo")
    hlapi_mock.reset_mock()

    # MIB with table, no symbols
    metrics = [{"MIB": "foo_mib", "table": "foo"}]
    with pytest.raises(Exception):
        config.parse_metrics(metrics, check.warning, check.log)

    # MIB with table and symbols
    metrics = [{"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"]}]
    table, _, _ = config.parse_metrics(metrics, check.warning, check.log)
    assert len(table) == 1
    assert len(table[0]) == 2
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "foo")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "bar")
    hlapi_mock.reset_mock()

    # MIB with table, symbols, bad metrics_tags
    metrics = [{"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"], "metric_tags": [{}]}]
    with pytest.raises(Exception):
        config.parse_metrics(metrics, check.warning, check.log)

    # MIB with table, symbols, bad metrics_tags
    metrics = [{"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"], "metric_tags": [{"tag": "foo"}]}]
    with pytest.raises(Exception):
        config.parse_metrics(metrics, check.warning, check.log)

    # Table with manual OID
    metrics = [{"MIB": "foo_mib", "table": "foo", "symbols": [{"OID": "1.2.3", "name": "foo"}]}]
    table, _, _ = config.parse_metrics(metrics, check.warning, check.log)
    assert len(table) == 1
    assert len(table[0]) == 1
    hlapi_mock.ObjectIdentity.assert_any_call("1.2.3")
    hlapi_mock.reset_mock()

    # MIB with table, symbols, metrics_tags index
    metrics = [
        {"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"], "metric_tags": [{"tag": "foo", "index": "1"}]}
    ]
    table, _, _ = config.parse_metrics(metrics, check.warning, check.log)
    assert len(table) == 1
    assert len(table[0]) == 2
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "foo")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "bar")
    hlapi_mock.reset_mock()

    # MIB with table, symbols, metrics_tags column
    metrics = [
        {"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"], "metric_tags": [{"tag": "foo", "column": "baz"}]}
    ]
    table, _, _ = config.parse_metrics(metrics, check.warning, check.log)
    assert len(table) == 1
    assert len(table[0]) == 3
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "foo")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "bar")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "baz")
    hlapi_mock.reset_mock()

    # MIB with table, symbols, metrics_tags column with OID
    metrics = [
        {
            "MIB": "foo_mib",
            "table": "foo",
            "symbols": ["foo", "bar"],
            "metric_tags": [{"tag": "foo", "column": {"name": "baz", "OID": "1.5.6"}}],
        }
    ]
    table, _, _ = config.parse_metrics(metrics, check.warning, check.log)
    assert len(table) == 1
    assert len(table[0]) == 3
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "foo")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "bar")
    hlapi_mock.ObjectIdentity.assert_any_call("1.5.6")
    hlapi_mock.reset_mock()


def test_profile_error():
    instance = common.generate_instance_config([])
    instance['profile'] = 'profile1'
    with pytest.raises(ConfigurationError):
        SnmpCheck('snmp', {}, [instance])

    init_config = {'profiles': {'profile1': {'definition_file': 'doesntexistfile'}}}
    with pytest.raises(ConfigurationError):
        SnmpCheck('snmp', init_config, [instance])

    with temp_dir() as tmp:
        profile_file = os.path.join(tmp, 'profile1.yaml')
        with open(profile_file, 'w') as f:
            f.write("not yaml: {")
        init_config = {'profiles': {'profile1': {'definition_file': profile_file}}}
        with pytest.raises(ConfigurationError):
            SnmpCheck('snmp', init_config, [instance])


def test_no_address():
    instance = common.generate_instance_config([])
    instance.pop('ip_address')
    with pytest.raises(ConfigurationError) as e:
        SnmpCheck('snmp', {}, [instance])
    assert str(e.value) == 'An IP address or a network address needs to be specified'


def test_both_addresses():
    instance = common.generate_instance_config(common.SUPPORTED_METRIC_TYPES)
    instance['network_address'] = '192.168.0.0/24'
    with pytest.raises(ConfigurationError) as e:
        SnmpCheck('snmp', {}, [instance])
    assert str(e.value) == 'Only one of IP address and network address must be specified'


def test_removing_host():
    """If a discovered host is failing 3 times in a row, we stop querying it."""
    instance = common.generate_instance_config(common.SUPPORTED_METRIC_TYPES)
    discovered_instance = instance.copy()
    discovered_instance['ip_address'] = '1.1.1.1'
    discovered_instance['retries'] = 0
    instance.pop('ip_address')
    instance['network_address'] = '192.168.0.0/24'
    check = SnmpCheck('snmp', {}, [instance])
    warnings = []
    check.warning = warnings.append
    check._config.discovered_instances['1.1.1.1'] = InstanceConfig(discovered_instance, None, None, [], '', {}, {})
    msg = 'No SNMP response received before timeout for instance 1.1.1.1'

    check.check(instance)
    assert warnings == [msg]

    check.check(instance)
    assert warnings == [msg, msg]

    check.check(instance)
    assert warnings == [msg, msg, msg]
    # Instance has been removed
    assert check._config.discovered_instances == {}

    check.check(instance)
    # No new warnings produced
    assert warnings == [msg, msg, msg]


@mock.patch("datadog_checks.snmp.snmp.read_persistent_cache")
def test_cache_discovered_host(read_mock):
    instance = common.generate_instance_config(common.SUPPORTED_METRIC_TYPES)
    instance.pop('ip_address')
    instance['network_address'] = '192.168.0.0/24'

    read_mock.return_value = '["192.168.0.1"]'
    check = SnmpCheck('snmp', {}, [instance])
    check.check(instance)

    assert '192.168.0.1' in check._config.discovered_instances


@mock.patch("datadog_checks.snmp.snmp.read_persistent_cache")
@mock.patch("datadog_checks.snmp.snmp.write_persistent_cache")
def test_cache_corrupted(write_mock, read_mock):
    instance = common.generate_instance_config(common.SUPPORTED_METRIC_TYPES)
    instance.pop('ip_address')
    instance['network_address'] = '192.168.0.0/24'
    read_mock.return_value = '["192.168.0."]'
    check = SnmpCheck('snmp', {}, [instance])
    check.check(instance)

    assert not check._config.discovered_instances
    write_mock.assert_called_once_with('', '[]')


@mock.patch("datadog_checks.snmp.snmp.read_persistent_cache")
@mock.patch("datadog_checks.snmp.snmp.write_persistent_cache")
def test_cache_building(write_mock, read_mock):
    instance = common.generate_instance_config(common.SUPPORTED_METRIC_TYPES)
    instance.pop('ip_address')

    read_mock.return_value = '[]'

    discovered_instance = instance.copy()
    discovered_instance['ip_address'] = '192.168.0.1'

    instance['network_address'] = '192.168.0.0/31'

    check = SnmpCheck('snmp', {}, [instance])

    check._config.discovered_instances['192.168.0.1'] = InstanceConfig(discovered_instance, None, None, [], '', {}, {})
    check._start_discovery()

    try:
        for _ in range(30):
            if write_mock.call_count:
                break
            time.sleep(0.5)
    finally:
        check._running = False

    write_mock.assert_called_once_with('', '["192.168.0.1"]')


def test_trie():
    trie = OIDTrie()
    trie.set((1, 2), 'bar')
    trie.set((1, 2, 3), 'foo')
    assert trie.match((1,)) == ((1,), None)
    assert trie.match((1, 2)) == ((1, 2), 'bar')
    assert trie.match((1, 2, 3)) == ((1, 2, 3), 'foo')
    assert trie.match((1, 2, 3, 4)) == ((1, 2, 3), 'foo')
    assert trie.match((2, 3, 4)) == ((), None)
