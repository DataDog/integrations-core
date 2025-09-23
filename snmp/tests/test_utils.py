# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Tuple  # noqa: F401

import pytest

from datadog_checks.snmp.exceptions import CouldNotDecodeOID, UnresolvedOID
from datadog_checks.snmp.metrics import as_metric_with_forced_type
from datadog_checks.snmp.models import OID
from datadog_checks.snmp.pysnmp_types import (
    MibViewController,
    ObjectIdentity,
    ObjectName,
    ObjectType,
    OctetString,
    SnmpEngine,
)
from datadog_checks.snmp.utils import transform_index

from . import common

pytestmark = common.snmp_integration_only


@pytest.mark.unit
def test_oid():
    # type: () -> None
    oid = OID((1, 3, 6, 1, 2, 1, 0))
    assert oid.as_tuple() == (1, 3, 6, 1, 2, 1, 0)
    assert repr(oid) == "OID('1.3.6.1.2.1.0')"
    assert str(oid) == '1.3.6.1.2.1.0'


@pytest.mark.unit
@pytest.mark.parametrize(
    'value, expected_tuple',
    [
        pytest.param((1, 3, 6, 1, 2, 1, 0), (1, 3, 6, 1, 2, 1, 0), id='tuple'),
        pytest.param('1.3.6.1.2.1.0', (1, 3, 6, 1, 2, 1, 0), id='string'),
        pytest.param((1, '3', 6, '1', 2, 1, '0'), (1, 3, 6, 1, 2, 1, 0), id='mixed-tuple'),
        pytest.param('.1.3.6.1.2.1.0', (1, 3, 6, 1, 2, 1, 0), id='string-with-leading-dot'),
        pytest.param(ObjectName((1, 3, 6, 1, 2, 1, 0)), (1, 3, 6, 1, 2, 1, 0), id='object-name-tuple'),
        pytest.param(ObjectName('1.3.6.1.2.1.0'), (1, 3, 6, 1, 2, 1, 0), id='object-name-string'),
        pytest.param(
            lambda controller: ObjectIdentity((1, 3, 6, 1, 2, 1, 0)).resolveWithMib(controller),
            (1, 3, 6, 1, 2, 1, 0),
            id='resolved-object-identity',
        ),
        pytest.param(
            lambda controller: ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 0))).resolveWithMib(controller),
            (1, 3, 6, 1, 2, 1, 0),
            id='resolved-object-type',
        ),
    ],
)
def test_oid_parse_valid(value, expected_tuple):
    # type: (Any, Tuple[int, ...]) -> None
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    if callable(value):
        value = value(mib_view_controller)
    assert OID(value).as_tuple() == expected_tuple


@pytest.mark.unit
@pytest.mark.parametrize(
    'value',
    [
        pytest.param((1, 2, 'a'), id='non-digit-parts'),
        pytest.param('1.2.a', id='non-digit-parts'),
        pytest.param('abc123', id='not-dot-separated-string'),
        pytest.param(True, id='not-tuple-or-str'),
        pytest.param(42, id='not-tuple-or-str'),
    ],
)
def test_oid_parse_invalid(value):
    # type: (Any) -> None
    with pytest.raises(CouldNotDecodeOID):
        OID(value)


@pytest.mark.unit
@pytest.mark.parametrize(
    'value, expected_tuple',
    [
        pytest.param(ObjectIdentity((1, 3, 6, 1, 2, 1, 0)), (1, 3, 6, 1, 2, 1, 0), id='object-identity'),
        pytest.param(ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 0))), (1, 3, 6, 1, 2, 1, 0), id='object-type'),
    ],
)
def test_oid_from_unresolved_instance(value, expected_tuple):
    # type: (Any, Tuple[int, ...]) -> None
    oid = OID(value)

    with pytest.raises(UnresolvedOID):
        oid.as_tuple()

    object_type = oid.as_object_type()

    # Verify returned ObjectType instance is valid by decoding it.
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    resolved = object_type.resolveWithMib(mib_view_controller)
    assert OID(resolved).as_tuple() == expected_tuple


@pytest.mark.unit
@pytest.mark.parametrize(
    'identity, mib, symbol, prefix',
    [
        pytest.param(lambda: ObjectIdentity('SNMPv2-MIB', 'sysDescr'), 'SNMPv2-MIB', 'sysDescr', (), id='no-prefix'),
        pytest.param(ObjectIdentity('1.3.6.1.2.1.1.1.0'), 'SNMPv2-MIB', 'sysDescr', ('0',), id='has-prefix'),
    ],
)
def test_oid_mib_symbol(identity, mib, symbol, prefix):
    # type: (ObjectIdentity, str, str, tuple) -> None
    if callable(identity):
        identity = identity()

    oid = OID(identity)

    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    oid.resolve(mib_view_controller)

    mib_symbol = oid.get_mib_symbol()
    assert mib_symbol.mib == mib
    assert mib_symbol.symbol == symbol
    assert mib_symbol.prefix == prefix


@pytest.mark.parametrize(
    'input_string,forced_type,expected',
    [
        pytest.param(10, 'gauge', {'type': 'gauge', 'value': 10}, id='gauge_integer'),
        pytest.param(OctetString(b'10\x00'), 'gauge', {'type': 'gauge', 'value': 10}, id='gauge_bytes'),
        pytest.param(OctetString(b'1.00\x00'), 'gauge', {'type': 'gauge', 'value': 1.0}, id='gauge_bytes_float'),
        pytest.param(OctetString('3.14'), 'gauge', {'type': 'gauge', 'value': 3.14}, id='gauge_float'),
        pytest.param(OctetString('3.14'), 'percent', {'type': 'rate', 'value': 314}, id='percent_float'),
        pytest.param(OctetString('3.14'), 'counter', {'type': 'rate', 'value': 3.14}, id='counter_float'),
        pytest.param(
            OctetString('3.14'),
            'monotonic_count',
            {'type': 'monotonic_count', 'value': 3.14},
            id='monotonic_count_float',
        ),
        pytest.param(
            OctetString('3.14'),
            'monotonic_count_and_rate',
            {'type': 'monotonic_count_and_rate', 'value': 3.14},
            id='monotonic_count_and_rate_float',
        ),
    ],
)
def test_as_metric_with_forced_type(input_string, forced_type, expected):
    assert expected == as_metric_with_forced_type(input_string, forced_type, options={})


@pytest.mark.parametrize(
    'src_index, transform_rules, expected_dst_index',
    [
        pytest.param(('10', '11', '12', '13'), [], (), id='no_transform_rules'),
        pytest.param(('10', '11', '12', '13'), [slice(2, 4)], ('12', '13'), id='one'),
        pytest.param(('10', '11', '12', '13'), [slice(2, 3), slice(0, 2)], ('12', '10', '11'), id='multi'),
        pytest.param(('10', '11', '12', '13'), [slice(2, 1000)], None, id='out_of_index_end'),
        pytest.param(('10', '11', '12', '13'), [slice(1000, 2000)], None, id='out_of_index_start_end'),
    ],
)
def test_transform_index(src_index, transform_rules, expected_dst_index):
    assert expected_dst_index == transform_index(src_index, transform_rules)
