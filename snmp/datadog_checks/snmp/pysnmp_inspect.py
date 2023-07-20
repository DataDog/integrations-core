# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for inspecting PySNMP objects.
"""
from typing import Any  # noqa: F401

from .pysnmp_types import ObjectIdentity, ObjectType  # noqa: F401


def _get_constructor_arguments(obj):
    # type: (Any) -> tuple
    # Several PySNMP objects store their `__init__` arguments into a private `__args` attribute, and their
    # public API prevents accessing that data until MIB resolution has occurred.
    # HACK: If the data we care about is in those arguments (eg the OID string in `ObjectIdentity('1.2.3...')`),
    # then we reach into private API to get it.
    attr_name = '_{}__args'.format(obj.__class__.__name__)
    return getattr(obj, attr_name)


def object_identity_from_object_type(object_type):
    # type: (ObjectType) -> ObjectIdentity
    # Assume `ObjectType(<object_identity>[, ...])`.
    args = _get_constructor_arguments(object_type)
    return args[0]


# HACK: we infer the types of SNMP values from their class names.
# Proper way would be to use the ASN.1 method `.isSameTypeWith()`, or at least `isinstance()`, but these
# wrongfully return `True` in some cases.
# For example, `CounterBasedGauge64` would be interpreted as a `Counter64` instead of a gauge.

SNMP_COUNTER_CLASSES = {
    'Counter32',
    'Counter64',
    # Additional types that are not part of the SNMP protocol (see RFC 2856).
    'ZeroBasedCounter64',
}

SNMP_GAUGE_CLASSES = {
    'Gauge32',
    'Integer',
    'Integer32',
    'Unsigned32',
    # Additional types that are not part of the SNMP protocol (see RFC 2856).
    'CounterBasedGauge64',
}


def is_counter(obj):
    # type: (Any) -> bool
    return obj.__class__.__name__ in SNMP_COUNTER_CLASSES


def is_gauge(obj):
    # type: (Any) -> bool
    return obj.__class__.__name__ in SNMP_GAUGE_CLASSES


def is_opaque(obj):
    # type: (Any) -> bool
    return obj.__class__.__name__ == 'Opaque'
