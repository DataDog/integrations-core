# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .marathon import Marathon
from .__about__ import __version__

__all__ = [
    'Marathon',
    '__version__'
]
