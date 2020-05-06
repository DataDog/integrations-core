# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import platform

import pytest

from datadog_checks.win32_event_log import Win32EventLogWMI

from . import common


@pytest.mark.integration
@pytest.mark.skipif(platform.system() != 'Windows', reason="Test only valid on Windows")
def test_basic_check(aggregator):
    check = Win32EventLogWMI('win32_event_log', {}, {}, [common.INSTANCE])
    check.check(common.INSTANCE)
    check.check(common.INSTANCE)
