# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Type declarations, for type checking purposes only.
"""
from typing import Literal, Set, TypedDict, Union

ForceableMetricType = Literal['gauge', 'percent']
MetricDefinition = TypedDict(
    'MetricDefinition', {'type': Literal['gauge', 'rate', 'counter', 'monotonic_count'], 'value': float}
)

# SNMP value types that we support.
# NOTE: these literals purposefully do NOT follow the names of PySNMP value classes.
# This is because they should be completely decoupled from PySNMP classes.
# Mapping from PySNMP classes to these literals is done elsewhere.
SNMPCounterType = Literal['counter32', 'counter64', 'zero-based-counter64']
SNMPGaugeType = Literal['gauge32', 'unsigned32', 'counter-based-gauge64', 'integer', 'integer32']
SNMPType = Union[SNMPCounterType, SNMPGaugeType, Literal['opaque']]

SNMP_COUNTERS = {'counter32', 'counter64', 'zero-based-counter64'}  # type: Set[SNMPCounterType]
SNMP_GAUGES = {'gauge32', 'unsigned32', 'counter-based-gauge64', 'integer', 'integer32'}  # type: Set[SNMPGaugeType]
