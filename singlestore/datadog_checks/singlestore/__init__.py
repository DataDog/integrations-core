# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .check import SinglestoreCheck

__all__ = ['__version__', 'SinglestoreCheck']
