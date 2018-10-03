# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import psutil
import pytest
from mock import patch

from datadog_checks.process import ProcessCheck
from . import common

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
    p.memory_info().shared
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


def mock_find_pid(name, search_string, exact_match=True, ignore_ad=True,
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
def test_check(mock_process, aggregator):
    (minflt, cminflt, majflt, cmajflt) = [1, 2, 3, 4]

    def mock_get_pagefault_stats(pid):
        return [minflt, cminflt, majflt, cmajflt]

    process = ProcessCheck(common.CHECK_NAME, {}, {})
    config = common.get_config_stubs()
    for idx in range(len(config)):
        instance = config[idx]['instance']
        if 'search_string' not in instance.keys():
            process.check(instance)
        else:
            with patch('datadog_checks.process.ProcessCheck.find_pids',
                       return_value=mock_find_pid(instance['name'], instance['search_string'])):
                process.check(instance)

        # these are just here to ensure it passes the coverage report.
        # they don't really "test" for anything.
        for sname in common.PAGEFAULT_STAT:
            aggregator.assert_metric('system.processes.mem.page_faults.' + sname, at_least=0,
                                     tags=generate_expected_tags(instance))


@patch('psutil.Process', return_value=MockProcess())
def test_check_collect_children(mock_process, aggregator):
    instance = {
        'name': 'foo',
        'pid': 1,
        'collect_children': True
    }
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    process.check(instance)
    aggregator.assert_metric('system.processes.number', value=1, tags=generate_expected_tags(instance))


@patch('psutil.Process', return_value=MockProcess())
def test_check_filter_user(mock_process, aggregator):
    instance = {
        'name': 'foo',
        'pid': 1,
        'user': 'Bob'
    }
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    with patch('datadog_checks.process.ProcessCheck._filter_by_user', return_value={1, 2}):
        process.check(instance)

    aggregator.assert_metric('system.processes.number', value=2, tags=generate_expected_tags(instance))


def test_check_missing_pid(aggregator):
    instance = {
        'name': 'foo',
        'pid_file': '/foo/bar/baz'
    }
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    process.check(instance)
    aggregator.assert_service_check('process.up', count=1, status=process.CRITICAL)


def test_check_real_process(aggregator):
    "Check that we detect python running (at least this process)"
    from datadog_checks.utils.platform import Platform

    instance = {
        'name': 'py',
        'search_string': ['python'],
        'exact_match': False,
        'ignored_denied_access': True,
        'thresholds': {'warning': [1, 10], 'critical': [1, 100]},
    }
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    expected_tags = generate_expected_tags(instance)
    process.check(instance)
    for mname in common.PROCESS_METRIC:
        # cases where we don't actually expect some metrics here:
        #  - if io_counters() is not available
        #  - if memory_info_ex() is not available
        #  - first run so no `cpu.pct`
        if (not _PSUTIL_IO_COUNTERS and '.io' in mname) or (not _PSUTIL_MEM_SHARED and 'mem.real' in mname) \
                or mname == 'system.processes.cpu.pct':
            continue

        if Platform.is_windows():
            metric = common.UNIX_TO_WINDOWS_MAP.get(mname, mname)
        else:
            metric = mname
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)

    aggregator.assert_service_check('process.up', count=1, tags=expected_tags + ['process:py'])

    # this requires another run
    process.check(instance)
    aggregator.assert_metric('system.processes.cpu.pct', count=1, tags=expected_tags)
    aggregator.assert_metric('system.processes.cpu.normalized_pct', count=1, tags=expected_tags)


def test_check_real_process_regex(aggregator):
    "Check to specifically find this python pytest running process using regex."
    from datadog_checks.utils.platform import Platform

    instance = {
        'name': 'py',
        'search_string': ['.*python.*pytest'],
        'exact_match': False,
        'ignored_denied_access': True,
        'thresholds': {'warning': [1, 10], 'critical': [1, 100]},
    }
    process = ProcessCheck(common.CHECK_NAME, {}, {})
    expected_tags = generate_expected_tags(instance)
    process.check(instance)
    for mname in common.PROCESS_METRIC:
        # cases where we don't actually expect some metrics here:
        #  - if io_counters() is not available
        #  - if memory_info_ex() is not available
        #  - first run so no `cpu.pct`
        if (not _PSUTIL_IO_COUNTERS and '.io' in mname) or (not _PSUTIL_MEM_SHARED and 'mem.real' in mname) \
                or mname == 'system.processes.cpu.pct':
            continue

        if Platform.is_windows():
            metric = common.UNIX_TO_WINDOWS_MAP.get(mname, mname)
        else:
            metric = mname
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)

    aggregator.assert_service_check('process.up', count=1, tags=expected_tags + ['process:py'])

    # this requires another run
    process.check(instance)
    aggregator.assert_metric('system.processes.cpu.pct', count=1, tags=expected_tags)
    aggregator.assert_metric('system.processes.cpu.normalized_pct', count=1, tags=expected_tags)


def test_relocated_procfs(aggregator):
    import tempfile
    import shutil
    import uuid

    unique_process_name = str(uuid.uuid4())
    my_procfs = tempfile.mkdtemp()

    def _fake_procfs(arg, root=my_procfs):
        for key, val in arg.iteritems():
            path = os.path.join(root, key)
            if isinstance(val, dict):
                os.mkdir(path)
                _fake_procfs(val, path)
            else:
                with open(path, "w") as f:
                    f.write(str(val))
    _fake_procfs({
        '1': {
            'status': (
                "Name:\t{}\nThreads:\t1\n"
            ).format(unique_process_name),
            'stat': (
                '1 ({}) S 0 1 1 ' + ' 0' * 46
            ).format(unique_process_name),
            'statm': '10970 3014 2404 77 0 2242 0',
            'cmdline': unique_process_name,
            'fd': {},
            'io': (
                'rchar: 397865373\n'
                'wchar: 32186\n'
                'syscr: 2695852\n'
                'syscw: 202\n'
                'read_bytes: 1208320\n'
                'write_bytes: 0\n'
                'cancelled_write_bytes: 0\n'
            ),
        },
        'stat': (
            "cpu  13034 0 18596 380856797 2013 2 2962 0 0 0\n"
            "btime 1448632481\n"
        ),
    })

    config = {
        'init_config': {
            'procfs_path': my_procfs
        },
        'instances': [{
            'name': 'moved_procfs',
            'search_string': [unique_process_name],
            'exact_match': False,
            'ignored_denied_access': True,
            'thresholds': {'warning': [1, 10], 'critical': [1, 100]},
        }]
    }
    process = ProcessCheck(common.CHECK_NAME, config['init_config'], {}, config['instances'])

    try:
        with patch('socket.AF_PACKET', create=True), \
                patch('sys.platform', 'linux'), \
                patch('psutil._psutil_linux'), \
                patch('psutil._psutil_posix'):
            process.check(config["instances"][0])
    finally:
        shutil.rmtree(my_procfs)
        psutil.PROCFS_PATH = '/proc'

    expected_tags = generate_expected_tags(config['instances'][0])
    expected_tags += ['process:moved_procfs']
    aggregator.assert_service_check('process.up', count=1, tags=expected_tags)
