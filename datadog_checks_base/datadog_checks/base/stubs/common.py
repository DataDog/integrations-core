# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from collections import namedtuple

MetricStub = namedtuple('MetricStub', 'name type value tags hostname device')
ServiceCheckStub = namedtuple('ServiceCheckStub', 'check_id name status tags hostname message')
HistogramBucketStub = namedtuple('HistogramBucketStub', 'name value lower_bound upper_bound monotonic hostname tags')
