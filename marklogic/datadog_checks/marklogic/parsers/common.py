# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
<<<<<<< HEAD
from typing import Any, List, Optional, Tuple  # noqa: F401
=======
>>>>>>> 5f39deac0c (ignore existing F401)

from ..constants import GAUGE_UNITS


class MarkLogicParserException(RuntimeError):
    pass


def build_metric_to_submit(metric_name, value_data, tags=None):
    #  type: (str, Any, Optional[List[str]]) -> Optional[Tuple]
    if isinstance(value_data, (int, float)):
        return 'gauge', metric_name, value_data, tags
    elif 'units' in value_data and 'value' in value_data:
        units = value_data['units']
        value = value_data['value']
        if units in GAUGE_UNITS:
            return 'gauge', metric_name, value, tags
    else:
        raise MarkLogicParserException(
            "Invalid metric: metric_suffix={}, metric_data={}, tags={}".format(metric_name, value_data, tags)
        )
    return None


def is_metric(data):
    # type: (Any) -> bool
    return (isinstance(data, (int, float))) or ('units' in data and 'value' in data)
