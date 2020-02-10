# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .amazon_msk import AmazonMskCheck

__all__ = ['__version__', 'AmazonMskCheck']
