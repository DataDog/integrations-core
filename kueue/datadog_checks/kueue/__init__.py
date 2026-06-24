# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .check import KueueCheck

# Some Agent loader paths look for a generic `Check` symbol.
Check = KueueCheck

__all__ = ['__version__', 'KueueCheck', 'Check']
