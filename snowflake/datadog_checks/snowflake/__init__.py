# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# workaround for problem of platform.libc_ver() doesn't consider
# in case of sys.executable returns empty string on Python 3.8 or later
# Python issue link: https://bugs.python.org/issue42257
import sys

if not sys.executable:
    sys.executable = None  # type: ignore

from .__about__ import __version__
from .check import SnowflakeCheck

__all__ = ['__version__', 'SnowflakeCheck']
