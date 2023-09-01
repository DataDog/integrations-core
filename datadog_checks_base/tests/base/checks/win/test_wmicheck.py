# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev.testing import requires_windows

try:
    from datadog_checks.base.checks.win.wmi import WinWMICheck
except ImportError:
    pass


@requires_windows
def test_get_running_sampler_does_not_leak():
    check = WinWMICheck('wmi_base_check', {}, [{}])
    with check.get_running_wmi_sampler(properties=[], filters=[]) as sampler:
        assert sampler is not None
        assert check.get_running_wmi_sampler(properties=[], filters=[]) is sampler
