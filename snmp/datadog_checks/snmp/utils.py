# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from typing import Any, Dict, Mapping, Sequence, Tuple, Union

import yaml

from .compat import get_config
from .exceptions import CouldNotDecodeOID, SmiError
from .pysnmp_types import ObjectIdentity, ObjectName, ObjectType, endOfMibView, noSuchInstance


def get_profile_definition(profile):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    """
    Return the definition of an SNMP profile,
    either from the filesystem or from the profile configuration itself.

    Parameters:
    * profile (dict)

    Returns:
    * definition (dict)

    Raises:
    * Exception: if the definition file was not found or is malformed.
    """
    definition_file = profile.get('definition_file')

    if definition_file is not None:
        return _read_profile_definition(definition_file)

    return profile['definition']


def _get_profiles_root():
    # type: () -> str
    # NOTE: this separate helper function exists for mocking purposes.
    confd = get_config('confd_path')
    return os.path.join(confd, 'snmp.d', 'profiles')


def _get_profiles_site_root():
    here = os.path.dirname(__file__)
    return os.path.join(here, 'data', 'profiles')


def _read_profile_definition(definition_file):
    # type: (str) -> Dict[str, Any]
    if not os.path.isabs(definition_file):
        definition_conf_file = os.path.join(_get_profiles_root(), definition_file)
        if not os.path.isfile(definition_conf_file):
            definition_file = os.path.join(_get_profiles_site_root(), definition_file)
        else:
            definition_file = definition_conf_file

    with open(definition_file) as f:
        return yaml.safe_load(f)


def recursively_expand_base_profiles(definition):
    # type: (Dict[str, Any]) -> None
    """
    Update `definition` in-place with the contents of base profile files listed in the 'extends' section.

    Base profiles should be referenced by filename, which can be relative (built-in profile)
    or absolute (custom profile).

    Raises:
    * Exception: if any definition file referred in the 'extends' section was not found or is malformed.
    """
    extends = definition.get('extends', [])

    for filename in extends:
        base_definition = _read_profile_definition(filename)
        recursively_expand_base_profiles(base_definition)

        base_metrics = base_definition.get('metrics', [])
        existing_metrics = definition.get('metrics', [])
        definition['metrics'] = base_metrics + existing_metrics  # NOTE: base metrics must be added first.

        definition.setdefault('metric_tags', []).extend(base_definition.get('metric_tags', []))


def get_default_profiles():
    profiles = {}
    paths = [_get_profiles_site_root(), _get_profiles_root()]
    for path in paths:
        if not os.path.isdir(path):
            continue
        for filename in os.listdir(path):
            if filename.startswith('_'):
                continue
            base, ext = os.path.splitext(filename)
            if ext != '.yaml':
                continue
            profiles[base] = {'definition_file': os.path.join(path, filename)}
    return profiles


def parse_as_oid_tuple(value):
    # type: (Union[Sequence[int], str, ObjectName, ObjectIdentity, ObjectType]) -> Tuple[int, ...]
    """
    Given an OID in one of many forms, return its int-tuple representation.

    NOTE: not meant to be used directly -- use `models.OID` for a consistent interface instead.

    Raises:
    -------
    CouldNotDecodeOID:
        If `value` is of an unsupported type, or if it is supported by the OID could not be inferred from it.
    """
    if isinstance(value, (list, tuple)):
        # Eg: `(1, 3, 6, 1, 2, 1, 1, 1, 0)`
        try:
            return tuple(int(digit) for digit in value)
        except (TypeError, ValueError) as exc:
            raise CouldNotDecodeOID(exc)

    if isinstance(value, str):
        # Eg: ``'1.3.6.1.2.1.1.1.0'`

        # NOTE: There's an obscure and optional convention [0][1] that OIDs *CAN* be prefixed with a leading dot to
        # mark them as 'absolute', eg '.1.3.6.1.<etc>', as opposed to relative to a some non-agreed-upon root OID.
        # [0]: http://oid-info.com/faq.htm#mib
        # [1]: https://comp.protocols.snmp.narkive.com/3UtKdsqv/leading-dot-in-enterprise-oid-in-snmp-traps
        # This integration can only deal with absolute OIDs anyway, so let's assume that's what we get.
        value = value.lstrip('.')
        return parse_as_oid_tuple(value.split('.'))

    if isinstance(value, ObjectName):
        # Eg: ObjectName('1.3.6.1.2.1.1.1.0'), ObjectName((1, 3, 6, 1, 2, 1, 1, 1, 0)), etc.
        return value.asTuple()

    if isinstance(value, ObjectIdentity):
        # Eg: `ObjectIdentity('1.3.6.1.2.1.1.0').resolveWithMib(mibViewController)``
        # NOTE: inputs of this type most likely come from the execution of a PySNMP command.
        try:
            object_name = value.getOid()  # type: ObjectName
        except SmiError as exc:
            # Not resolved yet. Probably us building an `ObjectIdentity` instance manually...
            # We should be using our `OID` model in that case, so let's fail.
            raise CouldNotDecodeOID('Could not infer OID from `ObjectIdentity`: {!r}'.format(exc))

        return parse_as_oid_tuple(object_name)

    if isinstance(value, ObjectType):
        # Eg: `ObjectType(some_object_identity)`
        # NOTE: inputs of this type most likely come from the execution of a PySNMP command.
        try:
            object_identity = value[0]
        except SmiError as exc:
            # Not resolved yet. Probably us building an `ObjectType` instance manually...
            # We should be using our `OID` model in that case, so let's fail.
            raise CouldNotDecodeOID('Could not infer OID from `ObjectType`: {!r}'.format(exc))

        return parse_as_oid_tuple(object_identity)

    raise CouldNotDecodeOID('Building an OID from object {!r} of type {} is not supported'.format(value, type(value)))


def format_as_oid_string(parts):
    # type: (Tuple[int, ...]) -> str
    """
    Given an OID in int-tuple form, format it to the conventional dot-separated representation.
    """
    return '.'.join(str(part) for part in parts)


def oid_pattern_specificity(pattern):
    # type: (str) -> Tuple[int, Tuple[int, ...]]
    """Return a measure of the specificity of an OID pattern.

    Suitable for use as a key function when sorting OID patterns.
    """
    wildcard_key = -1  # Must be less than all digits, so that e.G. '1.*' is less specific than '1.n' for n = 0...9.

    parts = tuple(wildcard_key if digit == '*' else int(digit) for digit in pattern.lstrip('.').split('.'))

    return (
        len(parts),  # Shorter OIDs are less specific than longer OIDs, regardless of their contents.
        parts,  # For same-length OIDs, compare their contents (integer parts).
    )


class OIDPrinter(object):
    """Utility class to display OIDs efficiently.

    This is only meant for debugging, as it makes some assumptions on the data
    managed, and can be more expensive to use than regular display.
    """

    def __init__(self, oids, with_values):
        # type: (Union[Mapping, Sequence], bool) -> None
        self.oids = oids
        self.with_values = with_values

    def oid_str(self, oid):
        # type: (ObjectType) -> str
        """Display an OID object (or MIB symbol), even if the object is not initialized by PySNMP.

        Output:
            1.3.4.8.3.4
        """
        try:
            return oid[0].getOid().prettyPrint()
        except SmiError:
            # PySNMP screams when we try to access the name of an OID
            # that has no value yet. Fine, let's work around this arbitrary limitation...
            arg = oid._ObjectType__args[0]._ObjectIdentity__args[-1]
            if isinstance(arg, tuple):
                arg = '.'.join(map(str, arg))

            return arg

    def oid_str_value(self, oid):
        # type: (ObjectType) -> str
        """Display an OID object and its associated value.

        Output:
            '1.3.4.5.6': 57
        """
        if noSuchInstance.isSameTypeWith(oid[1]):
            value = "'NoSuchInstance'"
        elif endOfMibView.isSameTypeWith(oid[1]):
            value = "'EndOfMibView'"
        else:
            value = oid[1].prettyPrint()
            try:
                value = str(int(value))
            except (TypeError, ValueError):
                value = "'{}'".format(value)
        key = oid[0]
        if not isinstance(key, ObjectName):
            key = key.getOid()
        return "'{}': {}".format(key.prettyPrint(), value)

    def oid_dict(self, key, value):
        # type: (str, Dict[Any, Any]) -> str
        """Display a dictionary of OID results with indexes.

        This is tailored made for the structure we build for results in the check.

        Output:
            'ifInOctets: {'0': 3123, '1': 728}
        """
        values = []
        have_indexes = False
        for indexes, data in value.items():
            try:
                data = int(data)
            except (TypeError, ValueError):
                data = "'{}'".format(data)
            if indexes:
                values.append("'{}': {}".format('.'.join(indexes), data))
                have_indexes = True
            else:
                values.append(str(data))

        if not have_indexes:
            displayed = values[0]
        else:
            displayed = '{{{}}}'.format(', '.join(values))
        return "'{}': {}".format(key, displayed)

    def __str__(self):
        # type: () -> str
        if isinstance(self.oids, dict):
            return '{{{}}}'.format(', '.join(self.oid_dict(key, value) for (key, value) in self.oids.items()))
        if self.with_values:
            return '{{{}}}'.format(', '.join(self.oid_str_value(oid) for oid in self.oids))
        else:
            return '({})'.format(', '.join("'{}'".format(self.oid_str(oid)) for oid in self.oids))
