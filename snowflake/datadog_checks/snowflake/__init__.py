# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import sys

if not sys.executable:
    sys.executable = None

from .__about__ import __version__
from .check import SnowflakeCheck

__all__ = ['__version__', 'SnowflakeCheck']
