from typing import Any, Tuple

import pytest

from datadog_checks.snmp.exceptions import CouldNotDecodeOID, UnresolvedOID
from datadog_checks.snmp.models import OID
from datadog_checks.snmp.pysnmp_types import MibViewController, ObjectIdentity, ObjectName, ObjectType, SnmpEngine


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
    'identity, name, prefix',
    [
        pytest.param(lambda: ObjectIdentity('SNMPv2-MIB', 'sysDescr'), 'sysDescr', (), id='no-prefix'),
        pytest.param(ObjectIdentity('1.3.6.1.2.1.1.1.0'), 'sysDescr', ('0',), id='has-prefix'),
    ],
)
def test_oid_mib_symbol(identity, name, prefix):
    # type: (ObjectIdentity, str, tuple) -> None
    if callable(identity):
        identity = identity()

    oid = OID(identity)

    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    oid.resolve(mib_view_controller)

    symbol = oid.get_mib_symbol()
    assert symbol.name == name
    assert symbol.prefix == prefix
