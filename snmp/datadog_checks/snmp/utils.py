import os
from typing import Any, Dict, Tuple

import yaml
from pysnmp.proto.rfc1902 import ObjectName
from pysnmp.smi.error import SmiError
from pysnmp.smi.exval import endOfMibView, noSuchInstance

from .compat import get_config


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
    # NOTE: this separate helper function exists for mocking purposes.
    confd = get_config('confd_path')
    return os.path.join(confd, 'snmp.d', 'profiles')


def _read_profile_definition(definition_file):
    # type: (str) -> Dict[str, Any]
    if not os.path.isabs(definition_file):
        definition_file = os.path.join(_get_profiles_root(), definition_file)

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


def to_oid_tuple(oid):
    # type: (str) -> Tuple[int, ...]
    """Return a OID tuple from a OID string.

    Example:
    '1.3.6.1.4.1' -> (1, 3, 6, 1, 4, 1)
    """
    return tuple(map(int, oid.lstrip('.').split('.')))


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

    def __init__(self, oids, with_value):
        self.oids = oids
        self.with_value = with_value

    def oid_str(self, oid):
        try:
            return oid[0].getOid().prettyPrint()
        except SmiError:
            arg = oid._ObjectType__args[0]._ObjectIdentity__args[-1]
            if isinstance(arg, tuple):
                arg = '.'.join(map(str, arg))

            return arg

    def oid_str_value(self, oid):
        if noSuchInstance.isSameTypeWith(oid[1]):
            value = "'NoSuchInstance'"
        elif endOfMibView.isSameTypeWith(oid[1]):
            value = "'EndOfMibView'"
        else:
            value = oid[1].prettyPrint()
            try:
                value = int(value)
            except ValueError:
                value = "'{}'".format(value)
        key = oid[0]
        if not isinstance(key, ObjectName):
            key = key.getOid()
        return "'{}': {}".format(key.prettyPrint(), value)

    def oid_dict(self, key, value):
        values = []
        have_indexes = False
        for indexes, data in value.items():
            try:
                data = int(data)
            except ValueError:
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
        if isinstance(self.oids, dict):
            return '{{{}}}'.format(', '.join(self.oid_dict(key, value) for (key, value) in self.oids.items()))
        if self.with_value:
            return '{{{}}}'.format(', '.join(self.oid_str_value(oid) for oid in self.oids))
        else:
            return '({})'.format(', '.join("'{}'".format(self.oid_str(oid)) for oid in self.oids))
