# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .win32_event_log import Win32EventLogWMI

__all__ = [
    '__version__',
    'Win32EventLogWMI'
]
