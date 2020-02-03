# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Classes that model SNMP-related concepts, allowing us to work at a higher level
than what is provided out-of-the-box by PySNMP.
"""

from typing import Sequence, Tuple, Union

from .exceptions import SmiError
from .types import Asn1Type, ObjectIdentity, ObjectName, ObjectType, noSuchInstance, noSuchObject


class OID(object):
    """
    An SNMP object identifier.

    Acts as a facade for various types used by PySNMP to represent OIDs.
    """

    def __init__(self, obj):
        # type: (Union[str, Tuple[int, ...], ObjectIdentity, ObjectName]) -> None
        identifier = ()  # type: Tuple[int, ...]

        if isinstance(obj, str):
            identifier = tuple(map(int, obj.lstrip('.').split('.')))
        elif isinstance(obj, tuple):
            identifier = obj
        elif isinstance(obj, ObjectIdentity):
            try:
                identifier = obj.getOid().asTuple()
            except SmiError as exc:
                raise RuntimeError(
                    'Could not retrieve OID from `ObjectIdentity`: {!r}.\n'
                    'HINT: did you try passing an `ObjectIdentity` that was built manually? '
                    'This will only work it has been resolved, i.e. if you or someone else called '
                    '`.resolveWithMib(mibViewController)` on it. Note that this should have been done'
                    'done by PySNMP if this `ObjectIdentity` was obtained by executing an SNMP command.'.format(exc)
                )
        elif isinstance(obj, ObjectName):
            identifier = obj.asTuple()
        else:
            raise TypeError('Building an OID from object {!r} of type {} is not supported'.format(obj, type(obj)))

        self._identifier = identifier

    def as_tuple(self):
        # type: () -> Tuple[int, ...]
        return self._identifier

    def as_string(self):
        # type: () -> str
        return '.'.join(map(str, self.as_tuple()))

    def as_object_identity(self):
        # type: () -> ObjectIdentity
        return ObjectIdentity(self.as_tuple())

    def as_object_type(self):
        # type: () -> ObjectType
        return ObjectType(self.as_object_identity())

    def __repr__(self):
        # type: () -> str
        return 'OID({!r})'.format(self.as_string())


class Variable(object):
    """
    Represents the response of the SNMP host to a given requested OID.

    Also known as a 'MIB variable', or a 'var_bind' in the PySNMP jargon.
    """

    def __init__(self, var_bind):
        # type: (Union[ObjectType, Tuple]) -> None
        try:
            name = var_bind[0]  # type: Union[ObjectIdentity, ObjectName]
            value = var_bind[1]  # type: Asn1Type
        except SmiError as exc:
            raise RuntimeError(
                'Could not deconstruct MIB variable: {!r}.\n'
                'HINT: Did you try instantiating a `Variable()` object directly? '
                'This can only work if the given `ObjectType` has been resolved, i.e. someone '
                'called `.resolveWithMib(mibViewController)` on it. Note that this should have been done by '
                'PySNMP if this variable came from executing an SNMP command.'.format(exc)
            )
        else:
            self.oid = OID(name)
            self.value = value
            self.var_bind = var_bind

    @property
    def was_oid_found_by_snmp_host(self):
        # type: () -> bool
        return not noSuchInstance.isSameTypeWith(self.value) and not noSuchObject.isSameTypeWith(self.value)


class SNMPCommandResult(object):
    """
    Container for results of an SNMP command ran via PySNMP.

    For a description of PySNMP parameters, see:
    http://snmplabs.com/pysnmp/docs/hlapi/asyncore/sync/manager/cmdgen/getcmd.html

    Parameters
    ----------
    variables:
        The responses of the SNMP host for a set of requested OID.
        Each variable contains the OID and its value.
    error_indication:
        An error that occurred while requesting the SNMP host, e.g. a timeout, network failure, server error...
        (Same meaning as in PySNMP.)
    error_status:
        A protocol-level error, e.g. requesting an OID that doesn't exist.
        (Same meaning than in PySNMP.)
    error_variable:
        The variable at the source of the error, if any.
    """

    def __init__(
        self,
        variables,  # type: Tuple[Variable, ...]
        error_indication=None,  # type: Asn1Type
        error_status=None,  # type: Asn1Type
        error_variable=None,  # type: Variable
    ):
        self.variables = variables
        self.error_indication = error_indication
        self.error_status = error_status
        self.error_variable = error_variable

    @property
    def var_binds(self):
        # type: () -> Sequence[ObjectType]
        # Compat with debug logging of response variables.
        return [variable.var_bind for variable in self.variables]
