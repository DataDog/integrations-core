# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import win32pdh

# https://github.com/mhammond/pywin32/pull/1772#issuecomment-943793489
COUNTER_VALUE_FORMAT = win32pdh.PDH_FMT_DOUBLE | 0x00008000

# https://learn.microsoft.com/en-us/windows/win32/perfctrs/pdh-error-codes
# Success (positive values)
PDH_CSTATUS_VALID_DATA = 0
PDH_CSTATUS_NEW_DATA = 1

# Errors (negative values)
PDH_MORE_DATA = -2147481646  # 0x800007D2
PDH_INVALID_DATA = -1073738810  # 0xc0000bc6
PDH_CSTATUS_INVALID_DATA = -1073738822  # 0xc0000bba
