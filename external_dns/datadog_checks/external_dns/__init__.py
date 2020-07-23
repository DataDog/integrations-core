# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .external_dns import ExternalDNSCheck

__all__ = ['__version__', 'ExternalDNSCheck']
