# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .couch import CouchDb, BadConfigError, ConnectionError, BadVersionError

__all__ = [
    '__version__',
    'CouchDb',
    'BadConfigError',
    'ConnectionError',
    'BadVersionError',
]
