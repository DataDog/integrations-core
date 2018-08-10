# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .varnish import Varnish

__all__ = [
    "__version__",
    "Varnish"
]
