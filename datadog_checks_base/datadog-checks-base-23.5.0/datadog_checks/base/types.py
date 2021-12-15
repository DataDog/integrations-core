# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List, Literal, NamedTuple, Optional, Sequence, Tuple, TypedDict, Union

InitConfigType = Dict[str, Any]
AgentConfigType = Dict[str, Any]
InstanceType = Dict[str, Any]

ProxySettings = TypedDict(
    'ProxySettings', {'http': Optional[str], 'https': Optional[str], 'no': List[str]}, total=False
)

# NOTE: a bit involved, but this is basically a type checking-friendly `NamedTuple`-based version of an `Enum`.
# We don't use an actual `Enum` because for backwards compatibility we need e.g. `ServiceCheck.OK` to be
# `0` (the integer), instead of an opaque enum instance.
ServiceCheckStatus = Literal[0, 1, 2, 3]  # Can serve as an int enum type for type checking purposes.
_ServiceCheckType = NamedTuple(
    '_ServiceCheckType',
    [
        ('OK', ServiceCheckStatus),
        ('WARNING', ServiceCheckStatus),
        ('CRITICAL', ServiceCheckStatus),
        ('UNKNOWN', ServiceCheckStatus),
    ],
)
ServiceCheck = _ServiceCheckType(0, 1, 2, 3)  # For public enum-style use: `ServiceCheck.OK`, ...

ExternalTagType = Tuple[str, Dict[str, List[str]]]

Event = TypedDict(
    'Event',
    {
        'timestamp': int,
        'event_type': str,
        'api_key': str,
        'msg_title': str,
        'msg_text': str,
        'aggregation_key': str,
        'alert_type': Literal['error', 'warning', 'success', 'info'],
        'source_type_name': str,
        'host': str,
        'tags': Sequence[Union[str, bytes]],
        'priority': Literal['normal', 'low'],
    },
)
