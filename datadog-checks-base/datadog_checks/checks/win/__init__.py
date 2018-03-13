# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    # Agent5 compatibility layer
    from checks.libs.win.pdhbasecheck import PDHBaseCheck
except ImportError:
    from .winpdb_base import PDHBaseCheck

__all__ = [
    'PDHBaseCheck',
]
