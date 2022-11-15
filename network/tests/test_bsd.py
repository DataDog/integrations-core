# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import mock

from datadog_checks.network.check_bsd import BSDNetwork

from . import common
from .common import FIXTURE_DIR, decode_string


@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=True)
def test_returns_the_right_instance(is_bsd, is_linux, is_windows, check):
    check_instance = check({})
    assert isinstance(check_instance, BSDNetwork)


def ss_subprocess_mock(*args, **kwargs):
    with open(os.path.join(FIXTURE_DIR, 'mac_netstat'), 'rb') as f:
        contents = f.read()
        return decode_string(contents), None, None


def test_check_bsd(instance, aggregator):
    check = BSDNetwork('network', {}, [instance])
    with mock.patch('datadog_checks.network.check_bsd.get_subprocess_output') as out:
        out.side_effect = ss_subprocess_mock
        check.check({})
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
