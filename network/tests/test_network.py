# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy

import mock
import pytest
from six import PY3

from datadog_checks.dev import EnvVars

from . import common

if PY3:
    long = int


@pytest.mark.parametrize(
    "proc_location, envs, expected_net_proc_base_location",
    [
        ("/something/proc", {'DOCKER_DD_AGENT': 'true'}, "/something/proc/1"),
        ("/something/proc", {}, "/something/proc"),
        ("/proc", {'DOCKER_DD_AGENT': 'true'}, "/proc"),
        ("/proc", {}, "/proc"),
    ],
)
def test_get_net_proc_base_location(aggregator, check, proc_location, envs, expected_net_proc_base_location):
    check_instance = check(common.INSTANCE)
    with EnvVars(envs):
        actual = check_instance.get_net_proc_base_location(proc_location)
        assert expected_net_proc_base_location == actual


def test_invalid_excluded_interfaces(check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['excluded_interfaces'] = None
    check_instance = check(instance)
    result = check_instance.run()
    assert 'ConfigurationError' in result
    assert "Expected 'excluded_interfaces' to be a list, got 'NoneType'" in result


@pytest.mark.parametrize(
    "proc_location, ss_found, expected",
    [("/proc", False, True), ("/something/proc", False, False), ("/something/proc", True, True)],
)
def test_is_collect_cx_state_runnable(aggregator, check, proc_location, ss_found, expected):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_connection_state'] = True
    check_instance = check(instance)
    with mock.patch('datadog_checks.network.network.find_executable', lambda x: "/bin/ss" if ss_found else None):
        assert check_instance.is_collect_cx_state_runnable(proc_location) == expected
