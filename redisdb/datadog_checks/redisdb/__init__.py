# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .redisdb import Redis
from .__about__ import __version__

__all__ = [
    '__version__',
    'Redis'
]
