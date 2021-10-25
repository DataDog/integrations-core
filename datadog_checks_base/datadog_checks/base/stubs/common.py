# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from collections import namedtuple

MetricStubBase = namedtuple('MetricStub', 'name type value tags hostname device flush_first_value')


class MetricStub(MetricStubBase):
    def __new__(cls, name, type, value, tags, hostname, device, flush_first_value=None):
        return MetricStubBase.__new__(cls, name, type, value, tags, hostname, device, flush_first_value)


ServiceCheckStub = namedtuple('ServiceCheckStub', 'check_id name status tags hostname message')
HistogramBucketStubBase = namedtuple(
    'HistogramBucketStub',
    'name value lower_bound upper_bound monotonic hostname tags flush_first_value',
)


class HistogramBucketStub(HistogramBucketStubBase):
    def __new__(cls, name, value, lower_bound, upper_bound, monotonic, hostname, tags, flush_first_value=None):
        return HistogramBucketStubBase.__new__(
            cls, name, value, lower_bound, upper_bound, monotonic, hostname, tags, flush_first_value
        )
