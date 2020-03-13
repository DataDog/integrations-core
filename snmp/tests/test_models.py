from typing import Any, Tuple

import pytest

from datadog_checks.snmp.exceptions import CouldNotDecodeOID
from datadog_checks.snmp.models import OID, Value, Variable
from datadog_checks.snmp.pysnmp_types import (
    MibViewController,
    ObjectIdentity,
    ObjectName,
    ObjectType,
    SnmpEngine,
    noSuchInstance,
    noSuchObject,
)

pytestmark = pytest.mark.unit


def test_oid():
    # type: () -> None
    oid = OID((1, 3, 6, 1, 2, 1, 0))
    assert oid.resolve_as_tuple() == (1, 3, 6, 1, 2, 1, 0)
    assert oid == OID((1, 3, 6, 1, 2, 1, 0))
    assert oid != OID((1, 3, 6, 1, 4, 0))
    assert repr(oid) == "OID('1.3.6.1.2.1.0')"
    assert str(oid) == '1.3.6.1.2.1.0'


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


@pytest.mark.parametrize(
    'value, expected_tuple',
    [
        pytest.param(ObjectIdentity((1, 3, 6, 1, 2, 1, 0)), (1, 3, 6, 1, 2, 1, 0), id='object-identity',),
        pytest.param(ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 0))), (1, 3, 6, 1, 2, 1, 0), id='object-type',),
    ],
)
def test_oid_resolve_object_type_ok(value, expected_tuple):
    # type: (Any, Tuple[int, ...]) -> None
    oid = OID(value)
    object_type = oid.maybe_resolve_as_object_type()

    # Verify a valid ObjectType instance was indeed returned by decoding it.
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    resolved = object_type.resolveWithMib(mib_view_controller)
    assert OID(resolved).resolve_as_tuple() == (1, 3, 6, 1, 2, 1, 0)


def test_variable_number():
    # type: () -> None
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    var_bind = ObjectType(ObjectIdentity('IF-MIB', 'ifInErrors'), 2000).resolveWithMib(mib_view_controller)
    name, value = var_bind

    variable = Variable(oid=OID(name), value=Value(value))
    assert variable.oid == OID('1.3.6.1.2.1.2.2.1.14')

    assert variable.value
    assert str(variable.value) == '2000'
    assert int(variable.value) == 2000
    assert float(variable.value) == 2000.0


def test_variable_string():
    # type: () -> None
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    var_bind = ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr'), 'Linux x123').resolveWithMib(mib_view_controller)
    name, value = var_bind

    variable = Variable(oid=OID(name), value=Value(value))
    assert variable.oid == OID('1.3.6.1.2.1.1.1')

    assert variable.value
    assert str(variable.value) == 'Linux x123'
    with pytest.raises(ValueError):
        int(variable.value)
    with pytest.raises(ValueError):
        float(variable.value)


def test_variable_oid():
    # type: () -> None
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    var_bind = ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysObjectID', 0), '1.3.6.1').resolveWithMib(mib_view_controller)
    name, value = var_bind

    variable = Variable(oid=OID(name), value=Value(value))
    assert variable.oid == OID('1.3.6.1.2.1.1.2.0')

    assert variable.value
    assert str(variable.value) == '1.3.6.1'
    with pytest.raises(ValueError):
        int(variable.value)
    with pytest.raises(ValueError):
        float(variable.value)


def test_variable_no_such_instance():
    # type: () -> None
    """
    Example situation: server knows about the requested OID but it doesn't have a value to return.
    """
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    var_bind = ObjectType(ObjectIdentity('IF-MIB', 'ifInErrors'), noSuchInstance).resolveWithMib(mib_view_controller)
    name, value = var_bind
    variable = Variable(oid=OID(name), value=Value(value))
    assert not variable.value
    assert str(variable.value) == 'NoSuchInstance'
    with pytest.raises(ValueError):
        int(variable.value)
    with pytest.raises(ValueError):
        float(variable.value)


def test_variable_no_such_object():
    # type: () -> None
    """
    Example situation: server doesn't know about the requested OID.
    """
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    var_bind = ObjectType(ObjectIdentity('IF-MIB', 'ifInErrors'), noSuchObject).resolveWithMib(mib_view_controller)
    name, value = var_bind
    variable = Variable(oid=OID(name), value=Value(value))
    assert not variable.value
    assert str(variable.value) == 'NoSuchObject'
    with pytest.raises(ValueError):
        int(variable.value)
    with pytest.raises(ValueError):
        float(variable.value)
