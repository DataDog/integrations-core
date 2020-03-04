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

ServiceCheckStatus = Literal[0, 1, 2, 3]
_ServiceCheckType = NamedTuple(
    '_ServiceCheckType',
    [('OK', Literal[0]), ('WARNING', Literal[1]), ('CRITICAL', Literal[2]), ('UNKNOWN', Literal[3])],
)
ServiceCheck = _ServiceCheckType(0, 1, 2, 3)

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
