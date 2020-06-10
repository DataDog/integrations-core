# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import division

try:
    import pymqi
except ImportError:
    pymqi = None

CMQCFC_LOOKUP = {}

for attr in dir(pymqi.CMQCFC):
    if not attr.startswith('MQ'):
        continue
    val = getattr(pymqi.CMQCFC, attr)
    CMQCFC_LOOKUP[val] = attr
