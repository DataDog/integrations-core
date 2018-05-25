# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .oracle import Oracle, OracleConfigError
from .__about__ import __version__

__all__ = [
    "__version__",
    'Oracle',
    'OracleConfigError'
]
