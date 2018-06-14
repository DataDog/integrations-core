# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .windows_service import WindowsService

__all__ = [
    '__version__',
    'WindowsService'
]
