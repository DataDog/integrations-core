# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple

ServiceCheck = namedtuple('ServiceCheck', 'OK WARNING CRITICAL UNKNOWN')(0, 1, 2, 3)
