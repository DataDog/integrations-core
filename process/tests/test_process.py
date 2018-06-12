# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# import contextlib
import os
from mock import patch
import psutil
from datadog_checks.process import ProcessCheck
import common
import pytest

# cross-platform switches
_PSUTIL_IO_COUNTERS = True
try:
    p = psutil.Process(os.getpid())
    p.io_counters()
except Exception:
    _PSUTIL_IO_COUNTERS = False

_PSUTIL_MEM_SHARED = True
try:
    p = psutil.Process(os.getpid())
    p.memory_info_ex().shared
except Exception:
    _PSUTIL_MEM_SHARED = False


class MockProcess(object):
    def __init__(self):
        self.pid = None

    def is_running(self):
        return True

    def children(self, recursive=False):
        return []


def get_psutil_proc():
    return psutil.Process(os.getpid())


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def noop_get_pagefault_stats(pid):
    return None


def test_psutil_wrapper_simple(aggregator):
    # Load check with empty config
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    name = process.psutil_wrapper(
        get_psutil_proc(),
        'name',
        None,
        False
    )
    assert name is not None


def test_psutil_wrapper_simple_fail(aggregator):
    # Load check with empty config
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    name = process.psutil_wrapper(
        get_psutil_proc(),
        'blah',
        None,
        False
    )
    assert name is None


def test_psutil_wrapper_accessors(aggregator):
    # Load check with empty config
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    meminfo = process.psutil_wrapper(
        get_psutil_proc(),
        'memory_info',
        ['rss', 'vms', 'foo'],
        False
    )
    assert 'rss' in meminfo
    assert 'vms' in meminfo
    assert 'foo' not in meminfo


def test_psutil_wrapper_accessors_fail(aggregator):
    # Load check with empty config
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    meminfo = process.psutil_wrapper(
        get_psutil_proc(),
        'memory_infoo',
        ['rss', 'vms'],
        False
    )
    assert 'rss' not in meminfo
    assert 'vms' not in meminfo


def test_ad_cache(aggregator):
    config = {
        'instances': [{
            'name': 'python',
            'search_string': ['python'],
            'ignore_denied_access': 'false'
        }]
    }
    process = ProcessCheck(common.CHECK_NAME, {}, {}, config['instances'])

    def deny_name(obj):
        raise psutil.AccessDenied()

    with patch.object(psutil.Process, 'name', deny_name):
        with pytest.raises(psutil.AccessDenied):
            process.check(config['instances'][0])

    assert len(process.ad_cache) > 0

    # The next run shouldn't throw an exception
    process.check(config['instances'][0])
    # The ad cache should still be valid
    assert process.should_refresh_ad_cache('python') is False

    # Reset caches
    process.last_ad_cache_ts = {}
    process.last_pid_cache_ts = {}

    # Shouldn't throw an exception
    process.check(config['instances'][0])


def mock_find_pids(name, search_string, exact_match=True, ignore_ad=True,
                   refresh_ad_cache=True):
    if search_string is not None:
        idx = search_string[0].split('_')[1]

    config_stubs = common.get_config_stubs()
    return config_stubs[int(idx)]['mocked_processes']


def mock_psutil_wrapper(process, method, accessors, try_sudo, *args, **kwargs):
    if method == 'num_handles':  # win32 only
        return None
    if accessors is None:
        result = 0
    else:
        result = dict([(accessor, 0) for accessor in accessors])
    return result


def generate_expected_tags(instance):
    proc_name = instance['name']
    expected_tags = [proc_name, "process_name:{0}".format(proc_name)]
    if 'tags' in instance:
        expected_tags += instance['tags']
    return expected_tags


@patch('psutil.Process', return_value=MockProcess())
def test_check(aggregator):
    (minflt, cminflt, majflt, cmajflt) = [1, 2, 3, 4]

    def mock_get_pagefault_stats(pid):
        return [minflt, cminflt, majflt, cmajflt]

    mocks = {
        'find_pids': mock_find_pids,
        'psutil_wrapper': mock_psutil_wrapper,
        'get_pagefault_stats': mock_get_pagefault_stats,
    }

    config = {
        'instances': [stub['config'] for stub in common.get_config_stubs()]
    }