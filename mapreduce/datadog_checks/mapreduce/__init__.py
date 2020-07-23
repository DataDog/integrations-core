# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .mapreduce import MapReduceCheck

__all__ = ['__version__', 'MapReduceCheck']
