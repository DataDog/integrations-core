# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
from six import PY3

from datadog_checks.network.check_windows import WindowsNetwork

if PY3:
    long = int


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_creates_windows_instance(is_linux, is_bsd, is_solaris, is_windows, check):
    check_instance = check({})
    assert isinstance(check_instance, WindowsNetwork)
