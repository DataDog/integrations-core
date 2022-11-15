# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock

from datadog_checks.network.check_bsd import BSDNetwork


@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=True)
def test_returns_the_right_instance(is_bsd, is_linux, is_windows, check):
    check_instance = check({})
    assert isinstance(check_instance, BSDNetwork)
