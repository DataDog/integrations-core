# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import iteritems

from ..constants import GAUGE_UNITS


class CollectorException(RuntimeError):
    pass


def build_metric_to_submit(metric_name, value_data, tags=None):
    if isinstance(value_data, (int, float)):
        return 'gauge', metric_name, value_data, tags
    elif 'units' in value_data and 'value' in value_data:
        units = value_data['units']
        value = value_data['value']
        if units in GAUGE_UNITS:
            return 'gauge', metric_name, value, tags
    else:
        raise CollectorException("Invalid metric: metric_suffix={}, metric_data={}, tags={}".format(metric_name, value_data, tags))


def is_metric(data):
    return (isinstance(data, (int, float))) or ('units' in data and 'value' in data)
