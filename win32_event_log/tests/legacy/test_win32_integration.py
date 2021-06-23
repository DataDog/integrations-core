# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import platform

import pytest

from datadog_checks.win32_event_log import Win32EventLogCheck

from . import common


@pytest.mark.skipif(platform.system() != 'Windows', reason="Test only valid on Windows")
def test_basic_check(aggregator):
    check = Win32EventLogCheck('win32_event_log', {}, [common.INSTANCE])
    check.check(common.INSTANCE)  # First run just initialises timestamp
    check.check(common.INSTANCE)


def test_deprecation_notice(dd_run_check):
    check = Win32EventLogCheck('win32_event_log', {}, [common.INSTANCE])
    dd_run_check(check)
    assert (
        'This version of the check is deprecated and will be removed in a future release. '
        'Set `legacy_mode` to `false` and read about the latest options, such as `query`.'
    ) in check.get_warnings()
