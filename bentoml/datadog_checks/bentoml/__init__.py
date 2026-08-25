# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .check import BentomlCheck

__all__ = ['__version__', 'BentomlCheck']
