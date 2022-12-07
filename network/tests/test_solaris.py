# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import mock

from datadog_checks.network.check_solaris import SolarisNetwork

from . import common
from .common import FIXTURE_DIR, decode_string


@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=True)
def test_returns_the_right_instance(is_bsd, is_linux, is_windows, is_solaris, check):
    check_instance = check({})
    assert isinstance(check_instance, SolarisNetwork)


def ss_subprocess_mock(*args, **kwargs):
    if ['kstat', '-p', 'link:0:'] == args[0]:
        fixture = os.path.join(FIXTURE_DIR, 'solaris', 'kstat_p_link0')
    elif ["netstat", "-s", "-Ptcp"] == args[0]:
        fixture = os.path.join(FIXTURE_DIR, 'solaris', 'netstat_s_ptcp')
    with open(fixture, 'rb') as f:
        contents = f.read()
        return decode_string(contents), None, None


def test_check_solaris(instance, aggregator):
    check = SolarisNetwork('network', {}, [instance])
    with mock.patch('datadog_checks.network.check_solaris.get_subprocess_output') as out:
        out.side_effect = ss_subprocess_mock
        check.check({})
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric)
