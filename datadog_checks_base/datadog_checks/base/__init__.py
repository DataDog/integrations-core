# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__

__all__ = [
    '__version__'
]
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
