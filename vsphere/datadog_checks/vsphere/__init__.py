# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from .__about__ import __version__
from .vsphere import VSphereCheck

__all__ = ['__version__', 'VSphereCheck']
