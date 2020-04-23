# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List, NamedTuple, Tuple, Union

WMIMetric = NamedTuple('WMIMetric', [('name', str), ('value', float), ('tags', List[str])])
WMIProperties = Tuple[Dict[str, Tuple[str, str]], List[str]]
TagQuery = List[str]
WMIObject = Dict[str, Any]
WMIFilter = Union[str, List[str]]
