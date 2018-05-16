# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .couch import CouchDb
from . import errors

__all__ = [
    '__version__',
    'CouchDb',
    'errors',
]
