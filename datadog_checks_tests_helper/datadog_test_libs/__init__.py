# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from . import mock_dns

__all__ = [
    '__version__',
    'mock_dns'
]
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
