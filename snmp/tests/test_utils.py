from typing import Any, Tuple

import pytest

from datadog_checks.snmp.exceptions import CouldNotDecodeOID
from datadog_checks.snmp.models import OID, Variable
from datadog_checks.snmp.pysnmp_types import (
    Asn1Type,
    MibViewController,
    ObjectIdentity,
    ObjectName,
    ObjectType,
    SnmpEngine,
    noSuchInstance,
    noSuchObject,
)


@pytest.mark.unit
def test_oid():
    # type: () -> None
    oid = OID((1, 3, 6, 1, 2, 1, 0))
    assert oid.resolve_as_tuple() == (1, 3, 6, 1, 2, 1, 0)
    assert oid.resolve_as_string() == '1.3.6.1.2.1.0'
    assert oid == OID((1, 3, 6, 1, 2, 1, 0))
    assert oid != OID((1, 3, 6, 1, 4, 0))
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
def test_oid_parse_valid(value, expected_tuple):
    # type: (Any, Tuple[int, ...]) -> None
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    if callable(value):
        value = value(mib_view_controller)
    assert OID(value).resolve_as_tuple() == expected_tuple


@pytest.mark.unit
@pytest.mark.parametrize(
    'value, resolvable_as_object_type',
    [
        pytest.param((1, 2, 'a'), False, id='non-digit-parts'),
        pytest.param('1.2.a', False, id='non-digit-parts'),
        pytest.param('abc123', False, id='not-dot-separated-string'),
        pytest.param(True, False, id='not-tuple-or-str'),
        pytest.param(42, False, id='not-tuple-or-str'),
        pytest.param(ObjectIdentity((1, 3, 6, 1, 2, 1, 0)), True, id='unresolved-object-identity'),
        pytest.param(ObjectType(ObjectIdentity((1, 3, 6, 1, 2, 1, 0))), True, id='unresolved-object-type'),
    ],
)
def test_oid_parse_invalid(value, resolvable_as_object_type):
    # type: (Any, bool) -> None
    oid = OID(value)

    with pytest.raises(CouldNotDecodeOID):
        oid.resolve_as_tuple()

    with pytest.raises(CouldNotDecodeOID):
        oid.resolve_as_string()

    if resolvable_as_object_type:
        oid.maybe_resolve_as_object_type()
    else:
        with pytest.raises(CouldNotDecodeOID):
            oid.maybe_resolve_as_object_type()


@pytest.mark.unit
def test_variable():
    # type: () -> None
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())

    # Variable containing an OID.
    var_bind = ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysObjectID', 0), '1.3.6.1').resolveWithMib(mib_view_controller)
    variable = Variable.from_var_bind(var_bind)
    assert variable.oid == OID('1.3.6.1.2.1.1.2.0')
    assert isinstance(variable.value, OID)
    assert variable.value == OID('1.3.6.1')

    # Variable containing a number.
    var_bind = ObjectType(ObjectIdentity('IF-MIB', 'ifInErrors'), 2000).resolveWithMib(mib_view_controller)
    variable = Variable.from_var_bind(var_bind)
    assert variable.oid == OID('1.3.6.1.2.1.2.2.1.14')
    assert isinstance(variable.value, Asn1Type)
    assert variable.value.prettyPrint() == '2000'

    # Variable containing a string.
    var_bind = ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr'), 'Linux x123').resolveWithMib(mib_view_controller)
    variable = Variable.from_var_bind(var_bind)
    assert variable.oid == OID('1.3.6.1.2.1.1.1')
    assert isinstance(variable.value, Asn1Type)
    assert variable.value.prettyPrint() == 'Linux x123'


@pytest.mark.unit
def test_variable_was_oid_found():
    # type: () -> None
    mib_view_controller = MibViewController(SnmpEngine().getMibBuilder())
    var_bind = ObjectType(ObjectIdentity('IF-MIB', 'ifInErrors'), 2000).resolveWithMib(mib_view_controller)
    variable = Variable.from_var_bind(var_bind)
    assert Variable.was_oid_found(variable.value)

    assert not Variable.was_oid_found(noSuchInstance)
    assert not Variable.was_oid_found(noSuchObject)
