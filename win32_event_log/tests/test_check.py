# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.win32_event_log import Win32EventLogCheck

from .common import INSTANCE


def test_check():
    check = Win32EventLogCheck('win32_event_log', {}, [INSTANCE])

    with pytest.raises(NotImplementedError):
        check.check(INSTANCE)
