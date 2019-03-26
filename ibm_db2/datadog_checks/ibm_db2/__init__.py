# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .ibm_db2 import IbmDb2Check

__all__ = [
    '__version__',
    'IbmDb2Check'
]
