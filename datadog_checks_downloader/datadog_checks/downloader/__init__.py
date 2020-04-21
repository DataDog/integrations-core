# (C) Datadog, Inc. 2019-present
# CHANGED
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from .__about__ import __version__

# Do not log internal errors from the logging system
logging.raiseExceptions = False
__all__ = ['__version__']
