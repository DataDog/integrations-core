# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from tests.utils import requires_windows

try:
    from datadog_checks.base.checks.win.wmi import WinWMICheck
except ImportError:
    pass


@requires_windows
@pytest.mark.unit
def test_get_running_sampler_does_not_leak():
    check = WinWMICheck('wmi_base_check', {}, [{}])
    sampler = check.get_running_wmi_sampler(properties=[], filters=[])
    assert check.get_running_wmi_sampler(properties=[], filters=[]) is sampler
