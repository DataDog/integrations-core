# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, List, Literal, Optional, TypedDict, Union

MetricType = Literal['gauge', 'count', 'monotonic_count', 'rate', 'service_check']
Metric = TypedDict('Metric', {'type': MetricType, 'name': str, 'value': float, 'tags': List[str]})

MetricSpec = TypedDict(
    'MetricSpec',
    {
        'type': MetricType,
        'path': str,  # Used as the default name.
        'name': str,  # An explicit name for the metric.
        'transformer': Optional[Callable[[Any], Union[int, float]]],
    },
    total=False,
)

Enumeration = TypedDict('Enumeration', {'path': str, 'index_tag': str, 'metrics': List[MetricSpec]})

Group = TypedDict('Group', {'type': MetricType, 'path': str, 'key_tag': str})
