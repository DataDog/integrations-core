# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
import pytest

from datadog_checks.snmp.config import InstanceConfig

pytestmark = pytest.mark.unit


def warning(*args):
    pass


@mock.patch("datadog_checks.snmp.config.hlapi")
def test_parse_metrics(hlapi_mock):
    # No metrics
    metrics = []
    with pytest.raises(Exception):
        InstanceConfig.parse_metrics(metrics, False, warning)

    # Unsupported metric
    metrics = [{"foo": "bar"}]
    with pytest.raises(Exception):
        InstanceConfig.parse_metrics(metrics, False, warning)

    # Simple OID
    metrics = [{"OID": "1.2.3"}]
    table, raw, mibs = InstanceConfig.parse_metrics(metrics, False, warning)
    assert table == []
    assert mibs == set()
    assert len(raw) == 1
    hlapi_mock.ObjectIdentity.assert_called_once_with("1.2.3")
    hlapi_mock.reset_mock()

    # MIB with no symbol or table
    metrics = [{"MIB": "foo_mib"}]
    with pytest.raises(Exception):
        InstanceConfig.parse_metrics(metrics, False, warning)

    # MIB with symbol
    metrics = [{"MIB": "foo_mib", "symbol": "foo"}]
    table, raw, mibs = InstanceConfig.parse_metrics(metrics, False, warning)
    assert raw == []
    assert mibs == {"foo_mib"}
    assert len(table) == 1
    hlapi_mock.ObjectIdentity.assert_called_once_with("foo_mib", "foo")
    hlapi_mock.reset_mock()

    # MIB with table, no symbols
    metrics = [{"MIB": "foo_mib", "table": "foo"}]
    with pytest.raises(Exception):
        InstanceConfig.parse_metrics(metrics, False, warning)

    # MIB with table and symbols
    metrics = [{"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"]}]
    table, raw, mibs = InstanceConfig.parse_metrics(metrics, True, warning)
    assert raw == []
    assert mibs == set()
    assert len(table) == 2
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "foo")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "bar")
    hlapi_mock.reset_mock()

    # MIB with table, symbols, bad metrics_tags
    metrics = [{"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"], "metric_tags": [{}]}]
    with pytest.raises(Exception):
        InstanceConfig.parse_metrics(metrics, False, warning)

    # MIB with table, symbols, bad metrics_tags
    metrics = [{"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"], "metric_tags": [{"tag": "foo"}]}]
    with pytest.raises(Exception):
        InstanceConfig.parse_metrics(metrics, False, warning)

    # MIB with table, symbols, metrics_tags index
    metrics = [
        {"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"], "metric_tags": [{"tag": "foo", "index": "1"}]}
    ]
    table, raw, mibs = InstanceConfig.parse_metrics(metrics, True, warning)
    assert raw == []
    assert mibs == set()
    assert len(table) == 2
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "foo")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "bar")
    hlapi_mock.reset_mock()

    # MIB with table, symbols, metrics_tags column
    metrics = [
        {"MIB": "foo_mib", "table": "foo", "symbols": ["foo", "bar"], "metric_tags": [{"tag": "foo", "column": "baz"}]}
    ]
    table, raw, mibs = InstanceConfig.parse_metrics(metrics, True, warning)
    assert raw == []
    assert mibs == set()
    assert len(table) == 3
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "foo")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "bar")
    hlapi_mock.ObjectIdentity.assert_any_call("foo_mib", "baz")
    hlapi_mock.reset_mock()
