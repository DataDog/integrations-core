from typing import Any, Tuple

import pytest

from datadog_checks.snmp.exceptions import CouldNotDecodeOID
from datadog_checks.snmp.models import OID
from datadog_checks.snmp.pysnmp_types import MibViewController, ObjectIdentity, ObjectName, ObjectType, SnmpEngine

pytestmark = pytest.mark.unit


def test_oid():
    # type: () -> None
    oid = OID((1, 3, 6, 1, 2, 1, 0))
    assert oid.resolve_as_tuple() == (1, 3, 6, 1, 2, 1, 0)
    assert oid.resolve_as_string() == '1.3.6.1.2.1.0'
    assert oid == OID((1, 3, 6, 1, 2, 1, 0))
    assert oid != OID((1, 3, 6, 1, 4, 0))
    assert repr(oid) == "OID('1.3.6.1.2.1.0')"


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
            lambda controller: ObjectIdentity('SNMPv2-MIB', 'sysObjectID').resolveWithMib(controller),
            (1, 3, 6, 1, 2, 1, 1, 2),
            id='resolved-mib-object-identity',
        ),
        pytest.param(
            lambda controller: ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 0))).resolveWithMib(controller),
            (1, 3, 6, 1, 2, 1, 0),
            id='resolved-object-type',
        ),
    ],
)
def test_oid_resolve_ok(value, expected_tuple):
    # type: (Any, Tuple[int, ...]) -> None
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    if callable(value):
        value = value(mib_view_controller)
    assert OID(value).resolve_as_tuple() == expected_tuple


@pytest.mark.unit
@pytest.mark.parametrize(
    'value',
    [
        pytest.param((1, 2, 'a'), id='non-digit-parts'),
        pytest.param('1.2.a', id='non-digit-parts'),
        pytest.param('abc123', id='not-dot-separated-string'),
        pytest.param(True, id='not-tuple-or-str'),
        pytest.param(42, id='not-tuple-or-str'),
        pytest.param(ObjectIdentity((1, 3, 6, 1, 2, 1, 0)), id='unresolved-object-identity'),
        pytest.param(ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 0))), id='unresolved-object-type'),
    ],
)
def test_oid_resolve_failed(value):
    # type: (Any) -> None
    oid = OID(value)

    with pytest.raises(CouldNotDecodeOID):
        oid.resolve_as_tuple()

    with pytest.raises(CouldNotDecodeOID):
        oid.resolve_as_string()


@pytest.mark.parametrize(
    'value, expected_tuple',
    [
        pytest.param((1, 3, 6, 1, 2, 1, 0), (1, 3, 6, 1, 2, 1, 0), id='tuple'),
        pytest.param('1.3.6.1.2.1.0', (1, 3, 6, 1, 2, 1, 0), id='string'),
        pytest.param(ObjectIdentity((1, 3, 6, 1, 2, 1, 0)), (1, 3, 6, 1, 2, 1, 0), id='object-identity'),
        pytest.param(ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 0))), (1, 3, 6, 1, 2, 1, 0), id='object-type'),
    ],
)
def test_oid_as_object_type(value, expected_tuple):
    # type: (Any, Tuple[int, ...]) -> None
    oid = OID(value)
    object_type = oid.as_object_type()

    # Verify a valid ObjectType instance was indeed returned by decoding it.
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    resolved = object_type.resolveWithMib(mib_view_controller)
    assert OID(resolved).resolve_as_tuple() == (1, 3, 6, 1, 2, 1, 0)
