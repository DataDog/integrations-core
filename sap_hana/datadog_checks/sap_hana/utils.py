# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import re


def compact_query(query):
    return re.sub(r'\s+', ' ', query.strip())


def positive(*numbers):
    return max(0, *numbers)


def compute_percent(partial, total):
    if total:
        return partial / total * 100

    return 0
