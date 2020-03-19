# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, List, Literal, Optional, Sequence, TypedDict, Union

MetricType = Literal['gauge', 'count', 'monotonic_count', 'rate', 'service_check']
Metric = TypedDict('Metric', {'type': MetricType, 'name': str, 'value': float, 'tags': List[str]})

ModifierName = Literal['total', 'ok_warning', 'time_elapsed']
TotalModifier = TypedDict('TotalModifier', {'name': Literal['total'], 'map': Callable[[Any], Sequence]})
Modifier = Union[ModifierName, TotalModifier]

MetricSpec = TypedDict(
    'MetricSpec',
    {
        'type': MetricType,
        'path': str,  # Used as the default name.
        'name': str,  # An explicit name for the metric.
        'modifier': Optional[Modifier],
    },
    total=False,
)

Enumeration = TypedDict('Enumeration', {'path': str, 'index_tag': str, 'metrics': List[MetricSpec]})

Group = TypedDict('Group', {'path': str, 'key_tag': str, 'value_metric_type': MetricType})
