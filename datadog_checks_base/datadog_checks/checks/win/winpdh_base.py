# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.checks.win.winpdh_base import (
    int_types,
    double_types,
    PDHBaseCheck
)

try:
    from .winpdh import WinPDHCounter, DATA_TYPE_INT, DATA_TYPE_DOUBLE
except ImportError:
    from .winpdh_stub import WinPDHCounter, DATA_TYPE_INT, DATA_TYPE_DOUBLE
