# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    # Agent5 compatibility layer
    from checks.libs.win.pdhbasecheck import PDHBaseCheck
    from checks.libs.win.winpdh import WinPDHCounter
except ImportError:
    from .winpdh_base import PDHBaseCheck
    from .winpdh import WinPDHCounter


__all__ = [
    'PDHBaseCheck',
    'WinPDHCounter',
]
