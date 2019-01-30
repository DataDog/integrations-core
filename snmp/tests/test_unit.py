# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
import pytest

pytestmark = pytest.mark.unit


@mock.patch("datadog_checks.snmp.snmp.hlapi")
def test_parse_metrics(hlapi_mock, check):
    # No metrics
    metrics = []
    with pytest.raises(Exception):
        check.parse_metrics(metrics, False)

    # Unsupported metric
    metrics = [{
        "foo": "bar"
    }]
    with pytest.raises(Exception):
        check.parse_metrics(metrics, False)

    # Simple OID
    metrics = [{
        "OID": "1.2.3"
    }]
    table, raw, mibs = check.parse_metrics(metrics, False)
    assert table == []
    assert mibs == set()
    assert len(raw) == 1
    hlapi_mock.ObjectIdentity.assert_called_once_with("1.2.3")
    hlapi_mock.reset_mock()

    # MIB with no symbol or table
    metrics = [{
        "MIB": "foo_mib"
    }]
    with pytest.raises(Exception):
        check.parse_metrics(metrics, False)

    # MIB with symbol
    metrics = [{
        "MIB": "foo_mib",
        "symbol": "foo",
    }]
    table, raw, mibs = check.parse_metrics(metrics, False)
    assert raw == []
    assert mibs == {"foo_mib"}
    assert len(table) == 1
    hlapi_mock.ObjectIdentity.assert_called_once_with("foo_mib", "foo")
    hlapi_mock.reset_mock()

    # MIB with table
    metrics = [{
        "MIB": "foo_mib",
        "table": "foo",
    }]
    table, raw, mibs = check.parse_metrics(metrics, True)
    assert raw == []
    assert mibs == set()
    assert len(table) == 1
    hlapi_mock.ObjectIdentity.assert_called_once_with("foo_mib", "foo")
    hlapi_mock.reset_mock()
