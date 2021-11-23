# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import win32pdh

# https://github.com/mhammond/pywin32/pull/1772#issuecomment-943793489
COUNTER_VALUE_FORMAT = win32pdh.PDH_FMT_DOUBLE | 0x00008000
